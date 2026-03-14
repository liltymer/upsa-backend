from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO


def create_transcript_pdf(transcript_data: dict) -> BytesIO:
    """
    Generates a clean, structured academic transcript PDF.
    Returns a BytesIO buffer ready to be served as a file response.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor("#081C46"),
        alignment=1  # centre
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=4,
        textColor=colors.HexColor("#1227E2"),
        alignment=1
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#081C46")
    )

    normal_style = styles["Normal"]
    normal_style.fontSize = 10

    elements = []

    # -------------------------
    # HEADER
    # -------------------------

    elements.append(Paragraph("University of Professional Studies, Accra", title_style))
    elements.append(Paragraph("Unofficial Academic Transcript", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Student info table
    info_data = [
        ["Student Name:", transcript_data["student_name"]],
        ["Index Number:", transcript_data["index_number"]],
        ["Final CGPA:", str(transcript_data["cgpa"])],
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#081C46")),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.3 * inch))

    # -------------------------
    # SEMESTER RECORDS
    # -------------------------

    for semester in transcript_data["transcript"]:

        elements.append(
            Paragraph(
                f"Year {semester['year']} — Semester {semester['semester']}",
                section_style
            )
        )

        # Table header + rows
        table_data = [["Course Code", "Course Title", "Credits", "Grade", "Grade Point"]]

        for course in semester["courses"]:
            table_data.append([
                course["course_code"],
                course["course_title"],
                str(course["credits"]),
                course["grade"],
                str(course["grade_point"])
            ])

        # Semester GPA row
        table_data.append([
            "", "", "", "Semester GPA:", str(semester["semester_gpa"])
        ])

        col_widths = [1.1 * inch, 2.6 * inch, 0.7 * inch, 0.9 * inch, 1.0 * inch]

        semester_table = Table(table_data, colWidths=col_widths)
        semester_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1227E2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            # Data rows
            ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -2), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2),
             [colors.HexColor("#F5F7FF"), colors.white]),
            ("ALIGN", (2, 1), (-1, -2), "CENTER"),

            # GPA summary row
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 9),
            ("ALIGN", (3, -1), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, -1), (-1, -1), 6),

            # Grid
            ("GRID", (0, 0), (-1, -2), 0.4, colors.HexColor("#D0D7FF")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1227E2")),

            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        elements.append(semester_table)
        elements.append(Spacer(1, 0.15 * inch))

    # -------------------------
    # FINAL CGPA SUMMARY
    # -------------------------

    elements.append(Spacer(1, 0.2 * inch))

    summary_data = [
        ["Final CGPA", str(transcript_data["cgpa"])]
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#081C46")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    elements.append(summary_table)

    # -------------------------
    # BUILD PDF
    # -------------------------

    doc.build(elements)
    buffer.seek(0)

    return buffer