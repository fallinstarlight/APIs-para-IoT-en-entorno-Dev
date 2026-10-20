"""Small dependency/validation helpers shared by routers."""
from __future__ import annotations

from .errors import BadRequest


def ensure_positive_int(value: int, field: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise BadRequest(f"{field} must be a positive integer")
    return value


def require_non_empty(rows, *, what: str):
    if not rows:
        from .errors import ResourceNotFound

        raise ResourceNotFound(f"{what} not found")
    return rows