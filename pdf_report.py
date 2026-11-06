import io
import re
import html
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


def clean_text(value):
    import unicodedata
    import re

    if value is None:
        return ""

    text = str(value)

    replacements = {
        "\u2010": "-", "\u2011": "-", "\u2012": "-",
        "\u2013": "-", "\u2014": "-", "\u2212": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u00a0": " ", "\u2026": "...",
        "\u2022": "-", "\u00b7": "-",
        "\u2264": "<=", "\u2265": ">=",
        "\u20b9": "Rs.", "\u00d7": "x",
        "\u200b": "", "\ufeff": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\?([1-9]\d*)\?", r"[\1]", text)
    text = text.encode("latin-1", errors="replace").decode("latin-1")

    return text
def make_paragraph(text, style):
    text = clean_text(text).strip()
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return Paragraph(text, style)


def split_table_row(line):
    line = line.strip().strip("|")
    return [cell.strip() for cell in line.split("|")]


def is_table_separator(line):
    cells = split_table_row(line)
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None
        for cell in cells
    )


def add_markdown_table(lines, story, styles):
    rows = [split_table_row(line) for line in lines]
    if not rows:
        return

    column_count = max(len(row) for row in rows)
    normalized = []
    for row in rows:
        row = row + [""] * (column_count - len(row))
        normalized.append([
            Paragraph(html.escape(clean_text(cell)), styles["table"])
            for cell in row
        ])

    available_width = 174 * mm
    widths = [available_width / column_count] * column_count

    table = Table(
        normalized,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT"
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183153")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#B8C4D1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F1F5F9")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))


def add_report_body(report_text, story, styles):
    lines = str(report_text or "").splitlines()
    i = 0
    bullet_items = []

    def flush_bullets():
        nonlocal bullet_items
        for item in bullet_items:
            story.append(Paragraph(
                "- " + html.escape(clean_text(item)),
                styles["body"]
            ))
        bullet_items = []

    while i < len(lines):
        raw = lines[i].strip()
        line = clean_text(raw)

        if not line:
            flush_bullets()
            i += 1
            continue

        if i + 1 < len(lines) and "|" in raw and is_table_separator(lines[i + 1]):
            flush_bullets()
            table_lines = [raw]
            i += 2
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            add_markdown_table(table_lines, story, styles)
            continue

        if raw.startswith("# "):
            flush_bullets()
            story.append(Paragraph(
                html.escape(clean_text(raw[2:])), styles["ReportH1"]
            ))
            story.append(HRFlowable(
                width="100%", thickness=1,
                color=colors.HexColor("#2C5B8E"),
                spaceAfter=7
            ))
        elif raw.startswith("## "):
            flush_bullets()
            story.append(Paragraph(
                html.escape(clean_text(raw[3:])), styles["ReportH2"]
            ))
        elif raw.startswith("### "):
            flush_bullets()
            story.append(Paragraph(
                html.escape(clean_text(raw[4:])), styles["ReportH3"]
            ))
        elif raw.startswith(("- ", "* ")):
            bullet_items.append(raw[2:])
        elif re.match(r"^\d+[.)]\s+", raw):
            flush_bullets()
            story.append(Paragraph(
                html.escape(clean_text(raw)), styles["body"]
            ))
        elif raw in ("---", "***", "___"):
            flush_bullets()
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#CBD5E1"),
                spaceBefore=5, spaceAfter=8
            ))
        else:
            flush_bullets()
            story.append(make_paragraph(raw, styles["body"]))

        i += 1

    flush_bullets()


def build_pdf_report(record):
    record = dict(record or {})
    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=21,
        leading=26, textColor=colors.HexColor("#183153"),
        alignment=TA_CENTER, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="Subtitle", parent=styles["Normal"],
        fontSize=10, leading=14, alignment=TA_CENTER,
        textColor=colors.HexColor("#526579"), spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name="ReportH1", parent=styles["Heading1"],
        fontSize=16, leading=20, textColor=colors.HexColor("#183153"),
        spaceBefore=13, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="ReportH2", parent=styles["Heading2"],
        fontSize=12, leading=16, textColor=colors.HexColor("#245B87"),
        spaceBefore=10, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="ReportH3", parent=styles["Heading3"],
        fontSize=10, leading=13, textColor=colors.HexColor("#334155"),
        spaceBefore=7, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="body", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=9,
        leading=13, textColor=colors.HexColor("#263445"),
        spaceAfter=6, alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name="table", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=7,
        leading=9, textColor=colors.HexColor("#263445")
    ))
    styles.add(ParagraphStyle(
        name="meta", parent=styles["BodyText"],
        fontSize=8, leading=11
    ))

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="Advanced Marketing Intelligence Report",
        author="Advanced Marketing Intelligence"
    )

    story = []
    story.append(Paragraph(
        "ADVANCED MARKETING INTELLIGENCE",
        styles["ReportTitle"]
    ))
    story.append(Paragraph(
        "Competitor Research &amp; Marketing Analysis",
        styles["Subtitle"]
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#245B87"),
        spaceAfter=12
    ))

    metadata = [
        ["Company / Brand", clean_text(record.get("company", "Not provided"))],
        ["Website", clean_text(record.get("website", "Not provided"))],
        ["Industry", clean_text(record.get("industry", "Not provided"))],
        ["Target Market", clean_text(record.get("market", "Not provided"))],
        ["Research Date", clean_text(record.get("timestamp", "Not provided"))],
        ["Search Results", clean_text(record.get("result_count", "Not provided"))],
    ]
    meta_data = [
        [Paragraph("<b>" + html.escape(k) + "</b>", styles["meta"]),
         Paragraph(html.escape(v), styles["meta"])]
        for k, v in metadata
    ]
    meta_table = Table(meta_data, colWidths=[43 * mm, 131 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 13))

    if record.get("goal"):
        story.append(Paragraph("Business Goal", styles["ReportH2"]))
        story.append(make_paragraph(record["goal"], styles["body"]))

    if record.get("competitors"):
        story.append(Paragraph("Competitors Covered", styles["ReportH2"]))
        story.append(make_paragraph(record["competitors"], styles["body"]))

    story.append(Paragraph("AI Marketing Analysis", styles["ReportH1"]))
    report = record.get("report", "")
    if not report:
        report = "No AI report content was saved for this research record."
    add_report_body(report, story, styles)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(
        width="100%", thickness=0.7,
        color=colors.HexColor("#CBD5E1")
    ))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This report is generated from saved research "
        "results and AI analysis. Verify important claims with original "
        "sources before making business decisions.",
        styles["body"]
    ))

    def add_page_footer(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(
            18 * mm, 9 * mm, "ADVANCED MARKETING INTELLIGENCE"
        )
        canvas.drawRightString(
            width - 18 * mm, 9 * mm, f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_footer,
              onLaterPages=add_page_footer)
    return buffer.getvalue()
