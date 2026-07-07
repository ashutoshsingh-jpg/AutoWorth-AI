"""
logger.py
---------
Sets up a rotating file logger used across the application.
Every prediction, request, and error is written to logs/app.log
so behaviour can be audited after deployment.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import Config


def setup_logger() -> logging.Logger:
    """
    Create and configure the application-wide logger.

    Returns:
        logging.Logger: A configured logger instance named "car_price_app".
    """
    os.makedirs(Config.LOGS_DIR, exist_ok=True)

    logger = logging.getLogger("car_price_app")
    logger.setLevel(logging.INFO)

    # Avoid attaching duplicate handlers if setup_logger() is called more than once
    # (e.g. under the Flask reloader in debug mode).
    if not logger.handlers:
        file_handler = RotatingFileHandler(
            Config.LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Also echo to console, which Render (and most PaaS platforms) captures
        # as part of the application's stdout logs.
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# A single shared logger instance to be imported across modules.
logger = setup_logger()
