"""Maps domain exceptions to HTTP responses with clean JSON bodies."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import (
    ConnectionFailure,
    DatabaseError,
    DuplicateResourceError,
    ForeignKeyError,
    InvalidProcedureArgumentError,
    NotFoundError,
    StoredProcedureError,
)


class APIError(Exception):
    """Base class for application-level errors with an HTTP status."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_error"

    def __init__(self, detail: str, *, error_code: str | None = None):
        super().__init__(detail)
        self.detail = detail
        if error_code:
            self.error_code = error_code


class BadRequest(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"


class Conflict(APIError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ResourceNotFound(APIError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class UnprocessableEntity(APIError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class ServiceUnavailable(APIError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "db_unavailable"


def _json(status_code: int, code: str, message: str, extra: dict | None = None):
    body = {"error": code, "detail": message}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError):
        return _json(exc.status_code, exc.error_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # Collapse pydantic errors into a readable list.
        problems = [
            {
                "loc": ".".join(str(p) for p in err.get("loc", [])),
                "msg": err.get("msg", "invalid value"),
                "type": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        return _json(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request payload failed validation",
            {"problems": problems},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return _json(
            exc.status_code,
            "http_error",
            str(exc.detail) if exc.detail else "HTTP error",
        )

    @app.exception_handler(DuplicateResourceError)
    async def _dup(_: Request, exc: DuplicateResourceError):
        return _json(status.HTTP_409_CONFLICT, "duplicate", str(exc))

    @app.exception_handler(ForeignKeyError)
    async def _fk(_: Request, exc: ForeignKeyError):
        return _json(status.HTTP_409_CONFLICT, "fk_violation", str(exc))

    @app.exception_handler(InvalidProcedureArgumentError)
    async def _bad_arg(_: Request, exc: InvalidProcedureArgumentError):
        return _json(status.HTTP_422_UNPROCESSABLE_ENTITY, "bad_argument", str(exc))

    @app.exception_handler(NotFoundError)
    async def _nf(_: Request, exc: NotFoundError):
        return _json(status.HTTP_404_NOT_FOUND, "not_found", str(exc))

    @app.exception_handler(ConnectionFailure)
    async def _conn(_: Request, exc: ConnectionFailure):
        return _json(status.HTTP_503_SERVICE_UNAVAILABLE, "db_unavailable", str(exc))

    @app.exception_handler(StoredProcedureError)
    async def _sp(_: Request, exc: StoredProcedureError):
        return _json(status.HTTP_500_INTERNAL_SERVER_ERROR, "db_error", str(exc))

    @app.exception_handler(DatabaseError)
    async def _db(_: Request, exc: DatabaseError):
        return _json(status.HTTP_500_INTERNAL_SERVER_ERROR, "db_error", str(exc))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        # Last-resort handler — never leak tracebacks to the client.
        import logging

        logging.getLogger("iotvehicule").exception("Unhandled exception")
        return _json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "Unexpected server error",
        )