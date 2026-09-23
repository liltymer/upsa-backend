from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1F3864")
LIGHT = colors.HexColor("#DCE3EE")
GRID = colors.HexColor("#000000")


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def create_transcript_pdf(transcript: dict) -> BytesIO:
    """
    Builds an unofficial transcript PDF for one programme, laid out like the
    UPSA transcript: per-semester tables with TCR / TGP / GPA / CGPA.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Transcript - {transcript['index_number'] or transcript['student_name']}",
    )
    width = doc.width
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontName="Times-Bold", fontSize=16, textColor=NAVY, spaceAfter=2)
    subtitle = ParagraphStyle("s", parent=styles["Normal"], fontName="Times-Bold", fontSize=10, alignment=1, spaceAfter=8)
    heading = ParagraphStyle("h", parent=styles["Normal"], fontName="Times-Bold", fontSize=10.5, textColor=NAVY,
                             alignment=1, spaceBefore=10, spaceAfter=4)
    cell = ParagraphStyle("c", parent=styles["Normal"], fontName="Times-Roman", fontSize=8.5, alignment=1, leading=10)
    small = ParagraphStyle("sm", parent=styles["Normal"], fontName="Times-Italic", fontSize=8, alignment=1,
                           textColor=colors.grey)

    elements = [
        Paragraph("UNIVERSITY OF PROFESSIONAL STUDIES, ACCRA", title),
        Paragraph("UNOFFICIAL TRANSCRIPT OF ACADEMIC RECORD", subtitle),
        Table([[""]], colWidths=[width], rowHeights=[4], style=[("BACKGROUND", (0, 0), (-1, -1), colors.black)]),
        Spacer(1, 8),
    ]

    info = Table(
        [
            ["Name:", Paragraph(escape(transcript["student_name"]), cell),
             "Student Number:", transcript["index_number"] or "-"],
            ["Programme:", Paragraph(escape(transcript["programme"]), cell),
             "Period:", transcript["period"]],
        ],
        colWidths=[width * 0.18, width * 0.34, width * 0.2, width * 0.28],
    )
    info.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(info)

    col_widths = [width * 0.14, width * 0.46, width * 0.13, width * 0.1, width * 0.17]

    for sem in transcript["transcript"]:
        rows = [["Code", "Course Title", "Credits", "Grade", "Grade Points"]]
        for c in sem["courses"]:
            rows.append([
                c["course_code"], Paragraph(escape(c["course_title"]), cell),
                _fmt(c["credits"]), c["grade"], _fmt(c["grade_value"]),
            ])
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ]))

        summary = Table(
            [[f"TCR: {_fmt(sem['total_credits'])}", f"TGP: {_fmt(sem['total_grade_points'])}",
              f"GPA: {_fmt(sem['semester_gpa'])}", f"CGPA: {_fmt(sem['cgpa'])}"]],
            colWidths=[width / 4] * 4,
        )
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("FONTNAME", (0, 0), (-1, -1), "Times-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        elements.append(KeepTogether([
            Paragraph(escape(sem["title"]), heading), table, Spacer(1, 4), summary,
        ]))

    standing = Table(
        [[f"Cumulative Credits: {_fmt(transcript['total_credits'])}",
          f"Cumulative Grade Points: {_fmt(transcript['total_grade_points'])}",
          f"CGPA: {_fmt(transcript['cgpa'])}",
          f"Class: {transcript['classification'] or '-'}"]],
        colWidths=[width * 0.24, width * 0.3, width * 0.16, width * 0.3],
    )
    standing.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("FONTNAME", (0, 0), (-1, -1), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements += [
        Paragraph("Overall Cumulative Standing", heading), standing, Spacer(1, 14),
        Paragraph(
            "Generated by GradeIQ UPSA from results entered by the student. "
            f"Not an official university document. Printed on {date.today():%A, %B %d, %Y}.",
            small,
        ),
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer
