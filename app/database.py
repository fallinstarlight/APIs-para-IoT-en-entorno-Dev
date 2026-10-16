"""Database access layer.

Wraps MySQL stored procedures and translates driver-level errors into
domain-level exceptions that the API layer can map to HTTP responses.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable, Optional

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error as MySQLError
from mysql.connector import errorcode

load_dotenv()

logger = logging.getLogger("iotvehicule.db")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "IotVehicle"),
    "autocommit": False,
    "connection_timeout": int(os.getenv("DB_CONN_TIMEOUT", "10")),
    "charset": "utf8mb4",
    "use_pure": True,
}


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------
class DatabaseError(Exception):
    """Base class for all DB-layer failures surfaced to the API."""


class DuplicateResourceError(DatabaseError):
    """A UNIQUE constraint (or duplicate PK) was violated."""


class ForeignKeyError(DatabaseError):
    """A referenced row is missing / still referenced by other rows."""


class NotFoundError(DatabaseError):
    """The procedure returned nothing where a row was required."""


class InvalidProcedureArgumentError(DatabaseError):
    """MySQL rejected the arguments (bad type / out of range / NULL)."""


class StoredProcedureError(DatabaseError):
    """The stored procedure itself raised SIGNAL / SQL exception."""


class ConnectionFailure(DatabaseError):
    """Could not reach / authenticate with MySQL."""


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------
@contextmanager
def get_connection():
    """Yield a MySQL connection; commit on success, rollback on any error."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except MySQLError as exc:
        logger.exception("MySQL connection failed")
        raise ConnectionFailure("Database is unreachable") from exc

    try:
        yield conn
        conn.commit()
    except MySQLError:
        try:
            conn.rollback()
        except MySQLError:
            logger.exception("Rollback failed")
        raise
    except Exception:
        # Non-DB exception inside the block — still rollback.
        try:
            conn.rollback()
        except MySQLError:
            logger.exception("Rollback failed")
        raise
    finally:
        try:
            conn.close()
        except MySQLError:
            logger.warning("Failed to close MySQL connection", exc_info=True)


def _serialize_value(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, timedelta):
        return v.total_seconds()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def _serialize_row(row: dict) -> dict:
    return {k: _serialize_value(v) for k, v in row.items()}


# ---------------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------------
def _translate_mysql_error(exc: MySQLError, proc_name: str) -> DatabaseError:
    code = exc.errno

    if code in (errorcode.ER_DUP_ENTRY, errorcode.ER_DUP_KEY):
        return DuplicateResourceError(f"Duplicate value for {proc_name}")
    if code in (
        errorcode.ER_NO_REFERENCED_ROW,
        errorcode.ER_NO_REFERENCED_ROW_2,
        errorcode.ER_ROW_IS_REFERENCED,
        errorcode.ER_ROW_IS_REFERENCED_2,
        errorcode.ER_BAD_NULL_ERROR,
    ):
        return ForeignKeyError(f"Referential integrity violation in {proc_name}")
    if code in (
        errorcode.ER_TRUNCATED_WRONG_VALUE,
        errorcode.ER_TRUNCATED_WRONG_VALUE_FOR_FIELD,
        errorcode.ER_WRONG_VALUE_FOR_TYPE,
        errorcode.ER_DATA_TOO_LONG,
        errorcode.ER_WARN_DATA_OUT_OF_RANGE,
        errorcode.WARN_DATA_TRUNCATED,
        errorcode.ER_BAD_FIELD_ERROR,
    ):
        return InvalidProcedureArgumentError(
            f"Invalid argument for {proc_name}"
        )
    if code in (
        errorcode.ER_SP_DOES_NOT_EXIST,
        errorcode.ER_SP_WRONG_NO_OF_ARGS,
        errorcode.ER_SP_NO_RETSET,
        errorcode.ER_SP_UNDECLARED_VAR,
        errorcode.ER_SIGNAL_EXCEPTION,
        errorcode.ER_SIGNAL_NOT_FOUND,
        errorcode.ER_SIGNAL_BAD_CONDITION_TYPE,
        errorcode.ER_UNKNOWN_PROCEDURE,
    ):
        return StoredProcedureError(f"Stored procedure {proc_name} failed")
    if code in (
        errorcode.CR_CONN_HOST_ERROR,
        errorcode.CR_SERVER_GONE_ERROR,
        errorcode.CR_SERVER_LOST,
        errorcode.ER_ACCESS_DENIED_ERROR,
        errorcode.ER_BAD_DB_ERROR,
    ):
        return ConnectionFailure("Database is unreachable")

    logger.exception("Unmapped MySQL error in %s (errno=%s)", proc_name, code)
    return StoredProcedureError(f"Database error while calling {proc_name}")


# ---------------------------------------------------------------------------
# Procedure helpers
# ---------------------------------------------------------------------------
def call_procedure(proc_name: str, args: Iterable[Any] = ()):
    """Call a stored procedure, returning the last non-empty result set."""
    args_tuple = tuple(args)
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.callproc(proc_name, args_tuple)
                result: list[dict] = []
                for rs in cursor.stored_results():
                    rows = rs.fetchall()
                    if rows:
                        result = [_serialize_row(r) for r in rows]
                return result
            finally:
                try:
                    cursor.close()
                except MySQLError:
                    logger.warning("Failed to close cursor", exc_info=True)
    except MySQLError as exc:
        raise _translate_mysql_error(exc, proc_name) from exc


def call_procedure_no_result(proc_name: str, args: Iterable[Any] = ()) -> None:
    """Execute a stored procedure discarding any result sets."""
    args_tuple = tuple(args)
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.callproc(proc_name, args_tuple)
                for _ in cursor.stored_results():
                    pass
            finally:
                try:
                    cursor.close()
                except MySQLError:
                    logger.warning("Failed to close cursor", exc_info=True)
    except MySQLError as exc:
        raise _translate_mysql_error(exc, proc_name) from exc


def procedure_exists(name: str) -> bool:
    """Return True if the named procedure exists in the current schema."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.ROUTINES "
                    "WHERE ROUTINE_SCHEMA = DATABASE() "
                    "AND ROUTINE_NAME = %s",
                    (name,),
                )
                (count,) = cur.fetchone()
                return bool(count)
            finally:
                try:
                    cur.close()
                except MySQLError:
                    pass
    except MySQLError:
        logger.exception("procedure_exists check failed for %s", name)
        return False