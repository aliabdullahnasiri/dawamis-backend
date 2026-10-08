from typing import cast

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.errors import AppError


async def app_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle application-level errors.
    """
    error = cast(AppError, exc)

    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": error.code,
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
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
    elif isinstance(exc, ValidationError):
        errors = exc.errors()
    else:
        raise TypeError(f"Unsupported validation error: {type(exc)!r}")

    status_code = 422

    for item in errors:
        ctx = item.get("ctx", {})

        if ctx.get("status_code"):
            status_code = ctx["status_code"]
            break

    return JSONResponse(
        status_code=status_code,
        content={
            "errors": jsonable_encoder(errors),
        },
    )
