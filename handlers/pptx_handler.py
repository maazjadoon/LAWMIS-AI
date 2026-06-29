"""
handlers/pptx_handler.py
────────────────────────
Fetches live KPI data from the LAWMIS database and generates a PPTX file.

Pipeline:
  1. Run structured SQL queries to collect all KPI metrics
  2. Build a structured KPI dict
  3. Call generators.pptx_generator.generate_pptx()
  4. Return a reply string with the saved file path

This handler does NOT use the KPI agent — it queries the DB directly for
structured data, which is more reliable for feeding into a template generator.
"""

import logging
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

import config
from agents.export_agent import run_export_agent
from handlers.export_handler import _extract_json
from handlers.report_helper import is_kpi_request, normalize_data_for_export, determine_export_title, clean_prompt_for_export
from generators.pptx_generator import generate_pptx, generate_tabular_pptx

logger = logging.getLogger(__name__)


def _connect():
    return psycopg2.connect(config.DB_URL)


def _fetch_kpi_data() -> dict:
    """Run all KPI queries and return a structured dict."""
    kpi: dict = {}

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # ── Workshops ────────────────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(*)                                        AS total,
                    COUNT(*) FILTER (WHERE workshop_status = 'Approved')   AS active,
                    COUNT(*) FILTER (WHERE workshop_status = 'Pending')  AS pending,
                    COUNT(*) FILTER (WHERE workshop_status = 'Rejected') AS rejected,
                    COUNT(*) FILTER (
                        WHERE DATE_TRUNC('month', approved_at) = DATE_TRUNC('month', CURRENT_DATE)
                    )                                               AS approved_this_month,
                    COUNT(*) FILTER (
                        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                    )                                               AS new_this_month
                FROM public.workshops;
            """)
            row = dict(cur.fetchone() or {})
            kpi["workshops"] = {k: (v if v is not None else "—") for k, v in row.items()}

            # ── Licenses ─────────────────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(*)                                                AS total,
                    COUNT(*) FILTER (WHERE license_status = 'Approved')      AS active,
                    COUNT(*) FILTER (WHERE license_status = 'Expired')     AS expired,
                    COUNT(*) FILTER (
                        WHERE valid_until BETWEEN CURRENT_DATE
                              AND CURRENT_DATE + INTERVAL '30 days'
                    )                                                       AS expiring_soon,
                    COALESCE(SUM(renewal_count), 0)                        AS total_renewals
                FROM public.workshop_licenses;
            """)
            row = dict(cur.fetchone() or {})
            kpi["licenses"] = {k: (v if v is not None else "—") for k, v in row.items()}

            # ── Payments ─────────────────────────────────────────────────────
            cur.execute("""
                SELECT
                    COALESCE(SUM(fee_amount) FILTER (WHERE payment_status = 'Paid'), 0)
                                                                AS total_revenue,
                    COALESCE(SUM(fee_amount) FILTER (
                        WHERE payment_status = 'Paid'
                          AND DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE)
                    ), 0)                                       AS revenue_this_month,
                    COUNT(*) FILTER (WHERE payment_status = 'Paid')    AS paid_count,
                    COUNT(*) FILTER (WHERE payment_status = 'Pending') AS pending_count,
                    ROUND(AVG(fee_amount) FILTER (WHERE payment_status = 'Paid'), 0)
                                                                AS avg_fee
                FROM public.payments;
            """)
            row = dict(cur.fetchone() or {})
            kpi["payments"] = {k: (int(v) if v is not None else "—") for k, v in row.items()}

            # ── Emission Tests ────────────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE test_date = CURRENT_DATE)  AS today,
                    COUNT(*)                                           AS total,
                    COUNT(DISTINCT vehicle_id)                         AS unique_vehicles,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE test_result = 'Pass')
                          / NULLIF(COUNT(*), 0), 1)                    AS pass_rate,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE test_result = 'Fail')
                          / NULLIF(COUNT(*), 0), 1)                    AS fail_rate
                FROM public.emission_tests;
            """)
            row = dict(cur.fetchone() or {})
            kpi["emission_tests"] = {k: (v if v is not None else "—") for k, v in row.items()}

            # ── Inspections ───────────────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(*)                                                    AS total,
                    COUNT(*) FILTER (WHERE inspection_result = 'Satisfactory') AS passed,
                    COUNT(*) FILTER (WHERE inspection_result = 'Conditional')  AS failed,
                    ROUND(AVG(total_score), 1)                                 AS avg_score,
                    COUNT(*) FILTER (WHERE follow_up_required = TRUE)          AS follow_up
                FROM public.rta_inspections;
            """)
            row = dict(cur.fetchone() or {})
            kpi["inspections"] = {k: (v if v is not None else "—") for k, v in row.items()}

            # ── Top 5 Cities ──────────────────────────────────────────────────
            cur.execute("""
                SELECT city, COUNT(*) AS count
                FROM public.workshops
                WHERE city IS NOT NULL AND city <> ''
                GROUP BY city
                ORDER BY count DESC
                LIMIT 5;
            """)
            kpi["top_cities"] = [dict(r) for r in cur.fetchall()]

            # ── Monthly Trends (last 6 months) ────────────────────────────────
            cur.execute("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', m.month), 'Mon YYYY') AS month,
                    COALESCE(w.cnt, 0)   AS new_workshops,
                    COALESCE(p.rev, 0)   AS revenue,
                    COALESCE(e.tests, 0) AS emission_tests
                FROM (
                    SELECT generate_series(
                        DATE_TRUNC('month', CURRENT_DATE - INTERVAL '5 months'),
                        DATE_TRUNC('month', CURRENT_DATE),
                        INTERVAL '1 month'
                    ) AS month
                ) m
                LEFT JOIN (
                    SELECT DATE_TRUNC('month', created_at) AS mo, COUNT(*) AS cnt
                    FROM public.workshops GROUP BY mo
                ) w ON w.mo = m.month
                LEFT JOIN (
                    SELECT DATE_TRUNC('month', payment_date) AS mo,
                           SUM(fee_amount) AS rev
                    FROM public.payments WHERE payment_status = 'Paid' GROUP BY mo
                ) p ON p.mo = m.month
                LEFT JOIN (
                    SELECT DATE_TRUNC('month', test_date) AS mo, COUNT(*) AS tests
                    FROM public.emission_tests GROUP BY mo
                ) e ON e.mo = m.month
                ORDER BY m.month;
            """)
            kpi["monthly_trends"] = [dict(r) for r in cur.fetchall()]

    return kpi


def handle_pptx(agent: Any, chat_input: str) -> str:
    """
    Fetch KPI data or custom query results, and generate a PPTX presentation.

    Parameters
    ----------
    agent      : Compiled export agent.
    chat_input : The user's original message.

    Returns
    -------
    User-facing reply string with the saved file path.
    """
    # ── Option A: Global KPI Dashboard slides ─────────────────────────────────
    if is_kpi_request(chat_input):
        logger.info("PPTX handler: General KPI request detected. Running dashboard build…")
        try:
            kpi = _fetch_kpi_data()
            path = generate_pptx(kpi)
            filename = Path(path).name
            return (
                f"✅ KPI PowerPoint presentation generated successfully!\n\n"
                f"📂 Saved to: {path}\n"
                f"🔗 Download Link: http://localhost:8000/exports/{filename}\n\n"
                f"The presentation contains 8 slides covering Workshops, Licenses, "
                f"Payments, Emission Tests, Inspections, Top Cities, and Monthly Trends."
            )
        except Exception as exc:
            logger.error("Global KPI PPTX generation failed: %s", exc)
            return f"I couldn't fetch the KPI data or build the PowerPoint presentation ({exc})."

    # ── Option B: Dynamic Query-specific Export slides ────────────────────────
    logger.info("PPTX handler: Specific dataset request detected. Running query-agent lookup…")
    try:
        cleaned_prompt = clean_prompt_for_export(chat_input)
        logger.info("PPTX handler: Cleaned prompt for export: %s", cleaned_prompt)
        raw_output = run_export_agent(agent, cleaned_prompt)
        records = _extract_json(raw_output)
    except Exception as exc:
        logger.error("Dynamic PPTX data query failed: %s", exc)
        return (
            f"I couldn't fetch the requested records to build the PowerPoint slides "
            f"({exc}). Please try again."
        )

    if not records:
        return "I queried the database but found no matching records to generate the PowerPoint slides."

    try:
        title = determine_export_title(records)
        # If user explicitly specified a filter (e.g. Quetta), append to title
        for word in ["quetta", "lahore", "karachi", "islamabad", "rawalpindi"]:
            if word in chat_input.lower():
                title = f"{title} ({word.title()})"
                break

        headers, rows = normalize_data_for_export(records)
        path = generate_tabular_pptx(headers, rows, title)
        filename = Path(path).name
        
        row_count = len(rows)
        disp_count = min(row_count, 50)
        return (
            f"✅ Custom PowerPoint presentation generated successfully!\n\n"
            f"📂 Saved to: {path}\n"
            f"🔗 Download Link: http://localhost:8000/exports/{filename}\n\n"
            f"The presentation contains slides displaying {disp_count} out of {row_count} matching records."
        )
    except Exception as exc:
        logger.error("Dynamic PPTX compilation failed: %s", exc)
        return f"I fetched the database records but failed to compile the PowerPoint slides ({exc})."

