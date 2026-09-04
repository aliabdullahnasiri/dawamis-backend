from typing import cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


async def request_validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle Pydantic request validation errors.
    """
    error = cast(RequestValidationError, exc)

    errors = error.errors()

    status_code = 422

    for item in errors:
        ctx = item.get("ctx", {})

        if ctx.get("status_code"):
            status_code = ctx["status_code"]
            break

    return JSONResponse(
        status_code=status_code,
        content={
            "errors": errors,
        },
    )
