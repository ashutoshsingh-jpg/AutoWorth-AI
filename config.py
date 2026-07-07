"""
config.py
---------
Centralized configuration for the Car Price Predictor application.

Every configurable value is read from an environment variable first, with a
sane local-development default as a fallback. This means nothing here needs
to be hardcoded for a given deployment target -- on Render (or any other
host), the real values are supplied via environment variables/secrets and
nothing in this file needs to change.

A `.env` file (loaded via python-dotenv, if present) is supported for local
development convenience. It is git-ignored and never required in production.
"""

import os

from dotenv import load_dotenv

# Load a local .env file if one exists. In production (Render, etc.) the
# real environment variables are injected by the platform instead, and this
# call is a harmless no-op if no .env file is found.
load_dotenv()

APP_VERSION: str = "1.0.0"


class Config:
    """Base application configuration, fully driven by environment variables."""

    # --- General ---
    APP_NAME: str = os.environ.get("APP_NAME", "ValueTrack AI")
    APP_VERSION: str = APP_VERSION
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # --- Paths ---
    BASE_DIR: str = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR: str = os.environ.get(
        "INSTANCE_DIR", os.path.join(BASE_DIR, "instance")
    )
    DATABASE_PATH: str = os.environ.get(
        "DATABASE_PATH", os.path.join(INSTANCE_DIR, "predictions.db")
    )

    LOGS_DIR: str = os.environ.get("LOGS_DIR", os.path.join(BASE_DIR, "logs"))
    LOG_FILE: str = os.environ.get("LOG_FILE", os.path.join(LOGS_DIR, "app.log"))

    MODEL_PATH: str = os.environ.get(
        "MODEL_PATH", os.path.join(BASE_DIR, "car_price_model.pkl")
    )

    REPORTS_DIR: str = os.environ.get(
        "REPORTS_DIR", os.path.join(BASE_DIR, "instance", "reports")
    )

    # --- Pagination ---
    HISTORY_PAGE_SIZE: int = int(os.environ.get("HISTORY_PAGE_SIZE", "10"))

    # --- Misc ---
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    ENV: str = os.environ.get("FLASK_ENV", "production")
