from typing import cast

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions.base import AppError


async def app_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle application-level errors.
    """
    error = cast(AppError, exc)

    return JSONResponse(
        status_code=error.code,
        content={
            "type": error.type,
            "message": error.message,
        },
    )


async def validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle Pydantic and FastAPI request validation errors.
    """
    if isinstance(exc, RequestValidationError) or isinstance(exc, ValidationError):
        errors = exc.errors()
    else:
        raise TypeError(f"Unsupported validation error: {type(exc)!r}")

    return JSONResponse(
        status_code=433,
        content={
            "errors": jsonable_encoder(errors),
        },
    )
