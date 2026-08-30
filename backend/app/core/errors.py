"""Centralised error handling: a few typed exceptions + FastAPI handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger("app.errors")


class AppError(Exception):
    """Base error for the application."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ProviderError(AppError):
    """Raised when an external data provider fails."""

    status_code = 502
    code = "provider_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        log.warning("app_error", code=exc.code, message=exc.message, status=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Internal server error."}},
        )
