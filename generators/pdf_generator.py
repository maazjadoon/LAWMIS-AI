"""
generators/pdf_generator.py
───────────────────────────
Generates a styled LAWMIS KPI PDF report from a structured KPI dict
using ReportLab.

Design:
  • Cover page  — navy header banner, title, date
  • Section pages — one section per KPI group (workshops, licenses, etc.)
  • Data tables   — alternating row colours, green header
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

import config

logger = logging.getLogger(__name__)

# ── Brand colours (ReportLab HexColor) ───────────────────────────────────────
NAVY    = colors.HexColor("#1B2A4A")
GREEN   = colors.HexColor("#2EA85E")
GREY_BG = colors.HexColor("#F4F6F9")
GREY_TXT= colors.HexColor("#55657A")
WHITE   = colors.white
BLACK   = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


def _styles() -> dict:
    """Return a dict of named ParagraphStyles."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KPITitle", parent=base["Title"],
            fontSize=28, textColor=WHITE, spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "KPISubtitle", parent=base["Normal"],
            fontSize=12, textColor=GREEN, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "KPISection", parent=base["Heading1"],
            fontSize=14, textColor=NAVY, spaceBefore=12, spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "kpi_label": ParagraphStyle(
            "KPILabel", parent=base["Normal"],
            fontSize=9, textColor=GREY_TXT,
        ),
        "kpi_value": ParagraphStyle(
            "KPIValue", parent=base["Normal"],
            fontSize=18, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "KPIBody", parent=base["Normal"],
            fontSize=10, textColor=BLACK,
        ),
    }


def _kpi_table(pairs: list[tuple[str, str]]) -> Table:
    """Render a list of (label, value) pairs as a 2-column table."""
    data = [["Metric", "Value"]] + list(pairs)
    col_widths = [10 * cm, 6 * cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 11),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        # Data rows — alternating bg
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("TEXTCOLOR",  (0, 1), (-1, -1), NAVY),
        ("FONTSIZE",   (0, 1), (-1, -1), 10),
        ("ALIGN",      (1, 1), (-1, -1), "RIGHT"),
        # Grid
        ("GRID",       (0, 0), (-1, -1), 0.4, GREY_TXT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _rank_table(headers: list[str], rows: list[list]) -> Table:
    """Render a ranked/trend table with multiple columns."""
    data = [headers] + rows
    col_w = (PAGE_W - 2 * MARGIN) / len(headers)
    t = Table(data, colWidths=[col_w] * len(headers), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 10),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("TEXTCOLOR",  (0, 1), (-1, -1), NAVY),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.4, GREY_TXT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def generate_pdf(kpi: dict) -> str:
    """
    Generate a styled PDF from a KPI data dict and save it to EXPORTS_DIR.

    Parameters
    ----------
    kpi : Structured KPI dict produced by handlers/pdf_handler.py.

    Returns
    -------
    Absolute path to the saved .pdf file.
    """
    exports_dir = Path(config.EXPORTS_DIR)
    exports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = exports_dir / filename

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )

    frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    styles = _styles()
    story: list = []
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")

    # ── Cover ────────────────────────────────────────────────────────────────
    # Navy banner drawn as a wide coloured table cell
    cover_data = [["LAWMIS KPI Dashboard"]]
    cover_table = Table(cover_data, colWidths=[PAGE_W - 2 * MARGIN])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, -1), WHITE),
        ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 26),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=3, color=GREEN))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Generated: {date_str}", styles["subtitle"]))
    story.append(Paragraph(
        "License &amp; Workshop Management Information System — Analytics Report",
        styles["body"],
    ))
    story.append(Spacer(1, 1 * cm))

    # ── Workshops ─────────────────────────────────────────────────────────────
    w = kpi.get("workshops", {})
    story.append(Paragraph("🏭  Workshops", styles["section"]))
    story.append(_kpi_table([
        ("Total Workshops",     str(w.get("total", "—"))),
        ("Active",              str(w.get("active", "—"))),
        ("Pending",             str(w.get("pending", "—"))),
        ("Rejected",            str(w.get("rejected", "—"))),
        ("Approved This Month", str(w.get("approved_this_month", "—"))),
        ("New This Month",      str(w.get("new_this_month", "—"))),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Licenses ──────────────────────────────────────────────────────────────
    lic = kpi.get("licenses", {})
    story.append(Paragraph("📄  Licenses", styles["section"]))
    story.append(_kpi_table([
        ("Total Licenses",       str(lic.get("total", "—"))),
        ("Active",               str(lic.get("active", "—"))),
        ("Expired",              str(lic.get("expired", "—"))),
        ("Expiring in 30 Days",  str(lic.get("expiring_soon", "—"))),
        ("Total Renewals",       str(lic.get("total_renewals", "—"))),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Payments ──────────────────────────────────────────────────────────────
    pay = kpi.get("payments", {})
    story.append(Paragraph("💰  Payments &amp; Revenue", styles["section"]))
    story.append(_kpi_table([
        ("Total Revenue",      f"PKR {pay.get('total_revenue', '—')}"),
        ("Revenue This Month", f"PKR {pay.get('revenue_this_month', '—')}"),
        ("Paid Payments",      str(pay.get("paid_count", "—"))),
        ("Pending Payments",   str(pay.get("pending_count", "—"))),
        ("Average Fee",        f"PKR {pay.get('avg_fee', '—')}"),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Emission Tests ────────────────────────────────────────────────────────
    em = kpi.get("emission_tests", {})
    story.append(Paragraph("🚗  Emission Tests", styles["section"]))
    story.append(_kpi_table([
        ("Tests Today",     str(em.get("today", "—"))),
        ("Total Tests",     str(em.get("total", "—"))),
        ("Pass Rate",       f"{em.get('pass_rate', '—')}%"),
        ("Failure Rate",    f"{em.get('fail_rate', '—')}%"),
        ("Unique Vehicles", str(em.get("unique_vehicles", "—"))),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Inspections ───────────────────────────────────────────────────────────
    ins = kpi.get("inspections", {})
    story.append(Paragraph("⭐  RTA Inspections", styles["section"]))
    story.append(_kpi_table([
        ("Total Inspections",  str(ins.get("total", "—"))),
        ("Passed",             str(ins.get("passed", "—"))),
        ("Failed",             str(ins.get("failed", "—"))),
        ("Average Score",      str(ins.get("avg_score", "—"))),
        ("Follow-up Required", str(ins.get("follow_up", "—"))),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Top Cities ────────────────────────────────────────────────────────────
    cities = kpi.get("top_cities", [])
    if cities:
        story.append(Paragraph("🏙️  Top Cities by Workshop Count", styles["section"]))
        rows = [[c.get("city", ""), str(c.get("count", ""))] for c in cities]
        story.append(_rank_table(["City", "Workshop Count"], rows))
        story.append(Spacer(1, 0.5 * cm))

    # ── Monthly Trends ────────────────────────────────────────────────────────
    trends = kpi.get("monthly_trends", [])
    if trends:
        story.append(Paragraph("📈  Monthly Trends (Last 6 Months)", styles["section"]))
        rows = [
            [
                t.get("month", ""),
                str(t.get("new_workshops", "—")),
                f"PKR {t.get('revenue', '—')}",
                str(t.get("emission_tests", "—")),
            ]
            for t in trends
        ]
        story.append(_rank_table(
            ["Month", "New Workshops", "Revenue", "Emission Tests"], rows
        ))

    doc.build(story)
    logger.info("PDF saved: %s", output_path)
    return str(output_path)


def generate_tabular_pdf(headers: list[str], rows: list[list[str]], title: str) -> str:
    """
    Generate a styled multi-page PDF document displaying a table of custom records.

    Parameters
    ----------
    headers : List of table column headers
    rows    : List of lists containing cell values (strings)
    title   : Description of the dataset (e.g. 'Workshops in Quetta')

    Returns
    -------
    Absolute path to the saved .pdf file.
    """
    exports_dir = Path(config.EXPORTS_DIR)
    exports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = exports_dir / filename

    col_count = len(headers)
    
    # Dynamically set page size and orientation: Portrait for <=8 columns, Landscape for >8 columns
    if col_count > 8:
        from reportlab.lib.pagesizes import landscape
        page_size = landscape(A4)
        page_w, page_h = page_size
    else:
        page_size = A4
        page_w, page_h = PAGE_W, PAGE_H

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=page_size,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )

    frame = Frame(MARGIN, MARGIN, page_w - 2 * MARGIN, page_h - 2 * MARGIN)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    styles = _styles()
    cell_style = ParagraphStyle(
        "TableCell", parent=styles["body"],
        fontSize=8, leading=10, textColor=NAVY
    )
    header_style = ParagraphStyle(
        "TableHeader", parent=styles["body"],
        fontSize=9, leading=11, fontName="Helvetica-Bold", textColor=WHITE,
        alignment=1  # Center
    )

    story: list = []
    date_str = datetime.now().strftime("%d %B %Y, %H:%M")

    # Header title banner
    banner_data = [[f"LAWMIS Data Export: {title}"]]
    banner_table = Table(banner_data, colWidths=[page_w - 2 * MARGIN])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, -1), WHITE),
        ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 16),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"Export Date: {date_str} | Total Records: {len(rows)}", styles["subtitle"]))
    story.append(Spacer(1, 0.5 * cm))

    # Convert all cell texts into Paragraph flowables to support auto-wrap
    table_data = []
    table_data.append([Paragraph(h, header_style) for h in headers])

    for row in rows:
        table_data.append([Paragraph(str(cell), cell_style) for cell in row])

    col_width = (page_w - 2 * MARGIN) / col_count

    t = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID",       (0, 0), (-1, -1), 0.4, GREY_TXT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    doc.build(story)
    logger.info("Tabular PDF saved: %s", output_path)
    return str(output_path)

