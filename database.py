"""
database.py
-----------
Lightweight SQLite persistence layer for prediction history.

No ORM is used on purpose -- the schema is tiny and plain SQL keeps the
project easy to read and deploy without extra dependencies. SQLite requires
no separate server, so this works out of the box on Render's free tier.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from config import Config
from logger import logger


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    Context manager that yields a SQLite connection with row access by column
    name, and guarantees the connection is closed afterwards.
    """
    os.makedirs(Config.INSTANCE_DIR, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Create the SQLite database file and the prediction_history table if they
    do not already exist. Safe to call every time the app starts.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                present_price   REAL NOT NULL,
                kms_driven      INTEGER NOT NULL,
                fuel_type       INTEGER NOT NULL,
                seller_type     INTEGER NOT NULL,
                transmission    INTEGER NOT NULL,
                owner           INTEGER NOT NULL,
                car_age         INTEGER NOT NULL,
                predicted_price REAL NOT NULL
            )
            """
        )
        conn.commit()
    logger.info("Database initialized (predictions.db ready).")


def save_prediction(data: Dict[str, Any]) -> int:
    """
    Insert a new prediction record.

    Args:
        data: Dictionary containing all prediction_history columns except
            'id' and 'timestamp', which are generated automatically.

    Returns:
        int: The row id of the newly inserted prediction.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO prediction_history
                (timestamp, present_price, kms_driven, fuel_type,
                 seller_type, transmission, owner, car_age, predicted_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                data["present_price"],
                data["kms_driven"],
                data["fuel_type"],
                data["seller_type"],
                data["transmission"],
                data["owner"],
                data["car_age"],
                data["predicted_price"],
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    logger.info(f"Prediction saved to history (id={new_id}, price={data['predicted_price']:.2f} Lakhs).")
    return new_id


def get_prediction_by_id(record_id: int) -> Optional[sqlite3.Row]:
    """Fetch a single prediction record by its id."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM prediction_history WHERE id = ?", (record_id,)
        ).fetchone()
    return row


_SORT_COLUMNS = {
    "latest": "id DESC",
    "oldest": "id ASC",
    "price_high": "predicted_price DESC",
    "price_low": "predicted_price ASC",
}


def _build_filters(search: str, date_from: str, date_to: str) -> tuple:
    """Shared WHERE-clause builder for get_history() and get_all_matching()."""
    conditions: List[str] = []
    params: List[Any] = []

    if search:
        conditions.append(
            """(CAST(predicted_price AS TEXT) LIKE ?
               OR CAST(present_price AS TEXT) LIKE ?
               OR CAST(kms_driven AS TEXT) LIKE ?
               OR CAST(car_age AS TEXT) LIKE ?)"""
        )
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term, like_term])

    if date_from:
        conditions.append("date(timestamp) >= date(?)")
        params.append(date_from)

    if date_to:
        conditions.append("date(timestamp) <= date(?)")
        params.append(date_to)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_clause, params


def get_history(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    sort: str = "latest",
) -> Dict[str, Any]:
    """
    Fetch a paginated, optionally search/date-filtered, sortable slice of
    prediction history.

    Args:
        page: 1-indexed page number.
        page_size: Number of rows per page.
        search: Optional search string matched against numeric columns.
        date_from: Optional 'YYYY-MM-DD' lower bound (inclusive) on timestamp.
        date_to: Optional 'YYYY-MM-DD' upper bound (inclusive) on timestamp.
        sort: One of 'latest', 'oldest', 'price_high', 'price_low'.

    Returns:
        dict with keys: records (list[sqlite3.Row]), total (int),
        page (int), total_pages (int).
    """
    offset = (page - 1) * page_size
    where_clause, params = _build_filters(search, date_from, date_to)
    order_clause = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["latest"])

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM prediction_history {where_clause}", params
        ).fetchone()["cnt"]

        records = conn.execute(
            f"""
            SELECT * FROM prediction_history
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "records": records,
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


def get_all_matching(
    search: str = "", date_from: str = "", date_to: str = "", sort: str = "latest"
) -> List[sqlite3.Row]:
    """Fetch every record matching the given filters (used for CSV export, unpaginated)."""
    where_clause, params = _build_filters(search, date_from, date_to)
    order_clause = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["latest"])

    with get_connection() as conn:
        records = conn.execute(
            f"SELECT * FROM prediction_history {where_clause} ORDER BY {order_clause}",
            params,
        ).fetchall()

    return records


def get_statistics() -> Dict[str, Any]:
    """
    Compute dashboard statistics: totals, today's count, price extremes,
    averages, and fuel-type distribution, plus a 7-day prediction trend.
    """
    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                AVG(predicted_price) AS avg_price,
                MAX(predicted_price) AS max_price,
                MIN(predicted_price) AS min_price,
                AVG(car_age) AS avg_car_age
            FROM prediction_history
            """
        ).fetchone()

        today_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM prediction_history "
            "WHERE date(timestamp) = date('now', 'localtime')"
        ).fetchone()["cnt"]

        fuel_rows = conn.execute(
            "SELECT fuel_type, COUNT(*) AS cnt FROM prediction_history GROUP BY fuel_type"
        ).fetchall()

        trend_rows = conn.execute(
            """
            SELECT date(timestamp) AS day, COUNT(*) AS cnt
            FROM prediction_history
            GROUP BY day
            ORDER BY day DESC
            LIMIT 7
            """
        ).fetchall()

    fuel_distribution = {"Petrol": 0, "Diesel": 0, "CNG": 0}
    fuel_labels = {0: "Petrol", 1: "Diesel", 2: "CNG"}
    for row in fuel_rows:
        label = fuel_labels.get(row["fuel_type"], "Other")
        fuel_distribution[label] = row["cnt"]

    return {
        "total": totals["total"] or 0,
        "today": today_count or 0,
        "avg_price": round(totals["avg_price"], 2) if totals["avg_price"] else 0.0,
        "max_price": round(totals["max_price"], 2) if totals["max_price"] else 0.0,
        "min_price": round(totals["min_price"], 2) if totals["min_price"] else 0.0,
        "avg_car_age": round(totals["avg_car_age"], 1) if totals["avg_car_age"] else 0.0,
        "fuel_distribution": fuel_distribution,
        "trend": [{"day": r["day"], "count": r["cnt"]} for r in reversed(trend_rows)],
    }


def delete_prediction(record_id: int) -> bool:
    """Delete a single prediction by id. Returns True if a row was deleted."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM prediction_history WHERE id = ?", (record_id,)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"Deleted prediction id={record_id} from history.")
    return deleted


def delete_all_predictions() -> int:
    """Delete every prediction record. Returns number of rows deleted."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM prediction_history")
        conn.commit()
        count = cursor.rowcount
    logger.info(f"Deleted all prediction history ({count} rows).")
    return count
