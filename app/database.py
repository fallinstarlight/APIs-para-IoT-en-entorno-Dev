import os
from contextlib import contextmanager
from typing import Any, Iterable, Optional
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()  # Load variables from .env into os.environ
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "IotVehicle"),
    "autocommit": False,
}


@contextmanager
def get_connection():
    """Yield a MySQL connection, commit on success, rollback on error."""
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-friendly types (datetime, Decimal) to primitives."""
    from datetime import datetime, date, timedelta
    from decimal import Decimal

    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, timedelta):
            out[k] = v.total_seconds()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, bytes):
            out[k] = v.decode("utf-8", errors="replace")
        else:
            out[k] = v
    return out


def call_procedure(proc_name: str, args: Iterable[Any] = ()):
    """
    Call a stored procedure and return the *last* result set as a list of dicts.
    If the procedure has no result set (e.g. UPDATE / DELETE / plain INSERT),
    returns an empty list.
    """
    result: list[dict] = []
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, tuple(args))
            # Drain all result sets; keep the last non-empty one
            for rs in cursor.stored_results():
                rows = rs.fetchall()
                if rows:
                    result = [_serialize_row(r) for r in rows]
        finally:
            cursor.close()
    return result


def call_procedure_no_result(proc_name: str, args: Iterable[Any] = ()):
    """Execute a stored procedure discarding any result sets."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.callproc(proc_name, tuple(args))
            # Drain any result sets so the connection is clean
            for _ in cursor.stored_results():
                pass
        finally:
            cursor.close()