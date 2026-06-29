"""
handlers/pdf_handler.py
───────────────────────
Fetches live KPI data from the LAWMIS database and generates a PDF report.
Shares _fetch_kpi_data logic with pptx_handler via a common import.
"""

import logging
from pathlib import Path
from typing import Any

import config
from agents.export_agent import run_export_agent
from handlers.export_handler import _extract_json
from handlers.report_helper import is_kpi_request, normalize_data_for_export, determine_export_title, clean_prompt_for_export
from generators.pdf_generator import generate_pdf, generate_tabular_pdf
from handlers.pptx_handler import _fetch_kpi_data   # reuse the same SQL queries

logger = logging.getLogger(__name__)


def handle_pdf(agent: Any, chat_input: str) -> str:
    """
    Fetch KPI data or custom query results, and generate a PDF report.

    Parameters
    ----------
    agent      : Compiled export agent.
    chat_input : The user's original message.

    Returns
    -------
    User-facing reply string with the saved file path.
    """
    # ── Option A: Global KPI Dashboard Report ─────────────────────────────────
    if is_kpi_request(chat_input):
        logger.info("PDF handler: General KPI request detected. Running dashboard build…")
        try:
            kpi = _fetch_kpi_data()
            path = generate_pdf(kpi)
            filename = Path(path).name
            return (
                f"✅ KPI PDF report generated successfully!\n\n"
                f"📂 Saved to: {path}\n"
                f"🔗 Download Link: http://localhost:8000/exports/{filename}\n\n"
                f"The report covers Workshops, Licenses, Payments, Emission Tests, "
                f"Inspections, Top Cities, and Monthly Trends."
            )
        except Exception as exc:
            logger.error("Global KPI PDF generation failed: %s", exc)
            return f"I couldn't fetch the KPI data or build the PDF report ({exc})."

    # ── Option B: Dynamic Query-specific Export Report ────────────────────────
    logger.info("PDF handler: Specific dataset request detected. Running query-agent lookup…")
    try:
        cleaned_prompt = clean_prompt_for_export(chat_input)
        logger.info("PDF handler: Cleaned prompt for export: %s", cleaned_prompt)
        raw_output = run_export_agent(agent, cleaned_prompt)
        logger.info("Raw export output: %r", raw_output[:300])
        records = _extract_json(raw_output)
        logger.info("Parsed records count: %d", len(records))
    except Exception as exc:
        logger.error("Dynamic PDF data query failed: %s", exc)
        return (
            f"I couldn't fetch the requested records to build the PDF report "
            f"({exc}). Please try again."
        )

    if not records:
        logger.warning("No records parsed from output: %r", raw_output)
        return "I queried the database but found no matching records to generate the PDF report."

    try:
        title = determine_export_title(records)
        # If user explicitly specified a filter (e.g. Quetta), append to title
        for word in ["quetta", "lahore", "karachi", "islamabad", "rawalpindi"]:
            if word in chat_input.lower():
                title = f"{title} ({word.title()})"
                break

        headers, rows = normalize_data_for_export(records)
        path = generate_tabular_pdf(headers, rows, title)
        filename = Path(path).name
        return (
            f"✅ Custom PDF report generated successfully!\n\n"
            f"📂 Saved to: {path}\n"
            f"🔗 Download Link: http://localhost:8000/exports/{filename}\n\n"
            f"The report contains a table displaying {len(rows)} matching records."
        )
    except Exception as exc:
        logger.error("Dynamic PDF compilation failed: %s", exc)
        return f"I fetched the database records but failed to compile the PDF report ({exc})."

