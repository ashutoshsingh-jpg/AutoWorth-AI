"""
utils.py
--------
Small, dependency-free helper functions shared across the app:
input validation, currency formatting, and price categorization.
None of these touch the ML model or its prediction logic.
"""

import csv
import io
from datetime import datetime
from typing import Any, Dict, Iterable, Tuple


class ValidationError(Exception):
    """Raised when user-submitted form data fails validation."""


def validate_and_parse_form(form: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate raw form input and convert it into the exact numeric types the
    model expects. Raises ValidationError with a friendly message on failure.

    The parsed keys/order are identical to the original app's feature set:
    present_price, kms_driven, fuel_type, seller_type, transmission, owner, car_age
    """
    try:
        present_price = float(form.get("present_price", ""))
    except (TypeError, ValueError):
        raise ValidationError("Present price must be a valid number (e.g. 6.5).")
    if present_price <= 0:
        raise ValidationError("Present price must be greater than 0.")

    try:
        kms_driven = int(float(form.get("kms_driven", "")))
    except (TypeError, ValueError):
        raise ValidationError("Kilometers driven must be a valid whole number.")
    if kms_driven < 0:
        raise ValidationError("Kilometers driven cannot be negative.")

    try:
        fuel_type = int(form.get("fuel_type", ""))
        seller_type = int(form.get("seller_type", ""))
        transmission = int(form.get("transmission", ""))
    except (TypeError, ValueError):
        raise ValidationError("Fuel type, seller type, and transmission must be valid selections.")

    try:
        owner = int(float(form.get("owner", "")))
    except (TypeError, ValueError):
        raise ValidationError("Number of previous owners must be a valid whole number.")
    if owner < 0:
        raise ValidationError("Number of previous owners cannot be negative.")

    try:
        car_age = int(float(form.get("car_age", "")))
    except (TypeError, ValueError):
        raise ValidationError("Car age must be a valid whole number.")
    if car_age < 0 or car_age > 60:
        raise ValidationError("Car age must be between 0 and 60 years.")

    return {
        "present_price": present_price,
        "kms_driven": kms_driven,
        "fuel_type": fuel_type,
        "seller_type": seller_type,
        "transmission": transmission,
        "owner": owner,
        "car_age": car_age,
    }


def format_currency(value: float) -> str:
    """Format a numeric Lakh value as an Indian Rupee currency string."""
    return f"₹ {value:,.2f} Lakhs"


def get_price_category(predicted_price: float) -> Tuple[str, str]:
    """
    Bucket a predicted price into a human-friendly category.

    Returns:
        (label, bootstrap_color_class) tuple, e.g. ("Mid-Range", "info").
    """
    if predicted_price < 3:
        return "Budget", "secondary"
    elif predicted_price < 7:
        return "Mid-Range", "info"
    elif predicted_price < 15:
        return "Premium", "warning"
    else:
        return "Luxury", "success"


def get_market_value_label(present_price: float, predicted_price: float) -> str:
    """
    Compare predicted resale price against present (original) price to give
    a simple qualitative market-value read out.
    """
    if present_price <= 0:
        return "Unknown"
    ratio = predicted_price / present_price
    if ratio >= 0.75:
        return "Excellent Resale Value"
    elif ratio >= 0.5:
        return "Good Resale Value"
    elif ratio >= 0.3:
        return "Fair Resale Value"
    else:
        return "Below Average Resale Value"


def current_timestamp_str() -> str:
    """Human-readable current timestamp, e.g. '05 Jul 2026, 03:45 PM'."""
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


FUEL_TYPE_LABELS = {0: "Petrol", 1: "Diesel", 2: "CNG"}
SELLER_TYPE_LABELS = {0: "Dealer", 1: "Individual"}
TRANSMISSION_LABELS = {0: "Manual", 1: "Automatic"}


def records_to_csv(records: Iterable[Any]) -> io.BytesIO:
    """
    Convert an iterable of sqlite3.Row prediction records into an in-memory
    CSV file, ready to be sent as a Flask attachment.
    """
    text_buffer = io.StringIO()
    writer = csv.writer(text_buffer)
    writer.writerow(
        [
            "ID", "Timestamp", "Present Price (Lakhs)", "KMs Driven",
            "Fuel Type", "Seller Type", "Transmission", "Owners",
            "Car Age (yrs)", "Predicted Price (Lakhs)",
        ]
    )
    for r in records:
        writer.writerow(
            [
                r["id"],
                r["timestamp"],
                r["present_price"],
                r["kms_driven"],
                FUEL_TYPE_LABELS.get(r["fuel_type"], r["fuel_type"]),
                SELLER_TYPE_LABELS.get(r["seller_type"], r["seller_type"]),
                TRANSMISSION_LABELS.get(r["transmission"], r["transmission"]),
                r["owner"],
                r["car_age"],
                r["predicted_price"],
            ]
        )

    byte_buffer = io.BytesIO(text_buffer.getvalue().encode("utf-8"))
    byte_buffer.seek(0)
    return byte_buffer
