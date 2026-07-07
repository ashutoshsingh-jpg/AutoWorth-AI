"""
report_generator.py
--------------------
Generates a downloadable PDF report summarizing a single prediction.
Uses reportlab, which is pure-Python and installs cleanly on Render.
"""

import io
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from config import Config
from utils import (
    FUEL_TYPE_LABELS,
    SELLER_TYPE_LABELS,
    TRANSMISSION_LABELS,
    format_currency,
    get_market_value_label,
    get_price_category,
)


def generate_prediction_report(record: Dict[str, Any]) -> io.BytesIO:
    """
    Build a one-page PDF report for a given prediction record.

    Args:
        record: dict-like row from prediction_history (must contain all
            standard columns: timestamp, present_price, kms_driven,
            fuel_type, seller_type, transmission, owner, car_age,
            predicted_price).

    Returns:
        io.BytesIO: An in-memory PDF buffer, seeked to position 0, ready to
            be sent as a Flask response.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        textColor=colors.HexColor("#1b5e20"),
        fontSize=22,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        textColor=colors.HexColor("#666666"),
        fontSize=11,
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#2e7d32"),
        spaceBefore=16,
        spaceAfter=8,
    )
    price_style = ParagraphStyle(
        "PriceStyle",
        parent=styles["Title"],
        textColor=colors.HexColor("#1b5e20"),
        fontSize=28,
        spaceBefore=10,
        spaceAfter=10,
    )

    elements = []

    # --- Header ---
    elements.append(Paragraph(f"{Config.APP_NAME}", title_style))
    elements.append(Paragraph("AI-Powered Car Valuation Report", subtitle_style))

    # --- Prediction highlight ---
    predicted_price = record["predicted_price"]
    elements.append(Paragraph("Estimated Selling Price", section_style))
    elements.append(Paragraph(format_currency(predicted_price), price_style))

    category, _ = get_price_category(predicted_price)
    market_value = get_market_value_label(record["present_price"], predicted_price)

    summary_table = Table(
        [
            ["Price Category", category],
            ["Market Value", market_value],
            ["Report Generated", record["timestamp"]],
        ],
        colWidths=[6 * cm, 9 * cm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f5e9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1b5e20")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8e6c9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(summary_table)

    # --- Input values used for prediction ---
    elements.append(Paragraph("Input Values", section_style))

    input_rows = [
        ["Field", "Value"],
        ["Present Price", format_currency(record["present_price"])],
        ["Kilometers Driven", f"{record['kms_driven']:,} km"],
        ["Fuel Type", FUEL_TYPE_LABELS.get(record["fuel_type"], "Unknown")],
        ["Seller Type", SELLER_TYPE_LABELS.get(record["seller_type"], "Unknown")],
        ["Transmission", TRANSMISSION_LABELS.get(record["transmission"], "Unknown")],
        ["Previous Owners", str(record["owner"])],
        ["Car Age", f"{record['car_age']} year(s)"],
    ]
    input_table = Table(input_rows, colWidths=[6 * cm, 9 * cm])
    input_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e7d32")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(input_table)

    elements.append(Spacer(1, 24))
    elements.append(
        Paragraph(
            f"Generated by {Config.APP_NAME} &mdash; predictions are estimates based on "
            "a trained machine learning model and should be used as guidance only.",
            subtitle_style,
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer
