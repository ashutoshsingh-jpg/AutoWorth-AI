"""
app.py
------
Used Car Price Predictor -- Flask application entry point.

IMPORTANT: The model loading and prediction logic below is preserved
EXACTLY as in the original project (same feature order, same
preprocessing -- i.e. none -- and same model.predict call). Everything
else (routing, history, dashboard, PDF reports, logging, health checks,
and the REST API) is new scaffolding built on top of that untouched core.
"""

import time
from typing import Any, Dict

import numpy as np
import pickle
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, g

from config import Config, APP_VERSION
from database import (
    init_db,
    save_prediction,
    get_history,
    get_all_matching,
    get_prediction_by_id,
    delete_prediction,
    delete_all_predictions,
    get_statistics,
)
from logger import logger
from report_generator import generate_prediction_report
from utils import (
    ValidationError,
    validate_and_parse_form,
    format_currency,
    get_price_category,
    get_market_value_label,
    current_timestamp_str,
    records_to_csv,
)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ---------------------------------------------------------------------------
# Model loading -- UNCHANGED from the original project.
# Do not alter this block: no retraining, no different preprocessing,
# no different feature order.
# ---------------------------------------------------------------------------
model = pickle.load(open(Config.MODEL_PATH, "rb"))

# Ensure the SQLite database + table exist before the app serves any request.
init_db()


def run_prediction(parsed: Dict[str, Any]) -> float:
    """
    Run the ML model on parsed/validated input.

    This mirrors the ORIGINAL app's prediction logic exactly:
    same feature order, same np.array shape, same model.predict call.
    """
    features = np.array(
        [
            [
                parsed["present_price"],
                parsed["kms_driven"],
                parsed["fuel_type"],
                parsed["seller_type"],
                parsed["transmission"],
                parsed["owner"],
                parsed["car_age"],
            ]
        ]
    )
    prediction = model.predict(features)[0]
    return float(prediction)


# ---------------------------------------------------------------------------
# Request/response logging -- timestamp, method, path, client IP, user agent,
# and total request duration, for every request the app handles.
# ---------------------------------------------------------------------------

@app.before_request
def _start_timer():
    g.request_start_time = time.perf_counter()


@app.after_request
def _log_request(response):
    duration_ms = None
    if hasattr(g, "request_start_time"):
        duration_ms = round((time.perf_counter() - g.request_start_time) * 1000, 2)

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "unknown")

    logger.info(
        f"{request.method} {request.path} -> {response.status_code} "
        f"| {duration_ms} ms | ip={client_ip} | ua=\"{user_agent}\""
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """Render the landing / prediction page."""
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """Handle the prediction form submission from the landing page."""
    try:
        parsed = validate_and_parse_form(request.form)
    except ValidationError as e:
        logger.warning(f"Validation error on /predict: {e}")
        flash(str(e), "danger")
        return render_template("index.html"), 400

    predict_start = time.perf_counter()
    try:
        predicted_price = run_prediction(parsed)
    except Exception as e:  # noqa: BLE001 - surface any model error to the user
        logger.error(f"Prediction error on /predict: {e}")
        flash("Something went wrong while generating the prediction. Please try again.", "danger")
        return render_template("index.html"), 500
    predict_duration_ms = round((time.perf_counter() - predict_start) * 1000, 2)

    record_id = save_prediction({**parsed, "predicted_price": predicted_price})
    logger.info(
        f"Prediction served via web form: {predicted_price:.2f} Lakhs "
        f"(id={record_id}, model_time={predict_duration_ms}ms)"
    )

    category, category_color = get_price_category(predicted_price)
    market_value = get_market_value_label(parsed["present_price"], predicted_price)

    result = {
        "id": record_id,
        "prediction_text": f"Estimated Car Price: {format_currency(predicted_price)}",
        "predicted_price": predicted_price,
        "formatted_price": format_currency(predicted_price),
        "prediction_time": current_timestamp_str(),
        "price_category": category,
        "price_category_color": category_color,
        "market_value": market_value,
    }

    return render_template("index.html", result=result)


@app.route("/history")
def history():
    """Display paginated, searchable, filterable, sortable prediction history."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    date_from = request.args.get("date_from", "", type=str).strip()
    date_to = request.args.get("date_to", "", type=str).strip()
    sort = request.args.get("sort", "latest", type=str).strip()

    if page < 1:
        page = 1

    data = get_history(
        page=page,
        page_size=Config.HISTORY_PAGE_SIZE,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    return render_template(
        "history.html",
        records=data["records"],
        total=data["total"],
        page=data["page"],
        total_pages=data["total_pages"],
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )


@app.route("/history/delete/<int:record_id>", methods=["POST"])
def history_delete(record_id: int):
    """Delete a single prediction from history."""
    deleted = delete_prediction(record_id)
    if deleted:
        flash("Prediction deleted successfully.", "success")
    else:
        flash("Prediction not found.", "warning")
    return redirect(url_for("history"))


@app.route("/history/delete_all", methods=["POST"])
def history_delete_all():
    """Delete all prediction history records."""
    count = delete_all_predictions()
    flash(f"Deleted {count} prediction(s) from history.", "success")
    return redirect(url_for("history"))


@app.route("/history/report/<int:record_id>")
def history_report(record_id: int):
    """Download a PDF report for a specific historical prediction."""
    record = get_prediction_by_id(record_id)
    if record is None:
        flash("Prediction not found.", "warning")
        return redirect(url_for("history"))

    buffer = generate_prediction_report(dict(record))
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"car_price_report_{record_id}.pdf",
    )


@app.route("/history/export")
def history_export():
    """Export the currently filtered/sorted history view as a CSV file."""
    search = request.args.get("search", "", type=str).strip()
    date_from = request.args.get("date_from", "", type=str).strip()
    date_to = request.args.get("date_to", "", type=str).strip()
    sort = request.args.get("sort", "latest", type=str).strip()

    records = get_all_matching(search=search, date_from=date_from, date_to=date_to, sort=sort)
    buffer = records_to_csv(records)
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name="prediction_history.csv",
    )


@app.route("/dashboard")
def dashboard():
    """Analytics dashboard: totals, price extremes, fuel mix, and 7-day trend."""
    stats = get_statistics()
    return render_template("dashboard.html", stats=stats)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    REST API endpoint for predictions.

    Accepts JSON body:
    {
        "present_price": 6.5,
        "kms_driven": 45000,
        "fuel_type": 0,
        "seller_type": 0,
        "transmission": 0,
        "owner": 0,
        "car_age": 5
    }

    Returns JSON with the prediction and derived fields.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"success": False, "error": "Request body must be valid JSON."}), 400

    try:
        parsed = validate_and_parse_form(payload)
    except ValidationError as e:
        logger.warning(f"Validation error on /api/predict: {e}")
        return jsonify({"success": False, "error": str(e)}), 422

    try:
        predicted_price = run_prediction(parsed)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Prediction error on /api/predict: {e}")
        return jsonify({"success": False, "error": "Prediction failed due to an internal error."}), 500

    record_id = save_prediction({**parsed, "predicted_price": predicted_price})
    logger.info(f"Prediction served via API: {predicted_price:.2f} Lakhs (id={record_id})")

    category, _ = get_price_category(predicted_price)
    market_value = get_market_value_label(parsed["present_price"], predicted_price)

    return jsonify(
        {
            "success": True,
            "id": record_id,
            "predicted_price": round(predicted_price, 2),
            "formatted_price": format_currency(predicted_price),
            "price_category": category,
            "market_value": market_value,
            "timestamp": current_timestamp_str(),
        }
    ), 201


@app.route("/health")
def health():
    """Liveness/readiness probe for Render (or any uptime monitor)."""
    return jsonify({"status": "healthy"}), 200


@app.route("/version")
def version():
    """Report application, model, and Python version info."""
    import sys

    return jsonify(
        {
            "app": Config.APP_NAME,
            "version": APP_VERSION,
            "python": sys.version.split()[0],
            "model": type(model).__name__,
        }
    ), 200


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Endpoint not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal server error: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Internal server error."}), 500
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
