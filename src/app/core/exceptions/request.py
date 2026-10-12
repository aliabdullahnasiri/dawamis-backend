from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class BadRequestError(AppError):
    """Raised when a request is invalid."""

    code = 400
    type = "bad_request"
    message = T("request:bad_request")


class ServiceUnavailableError(AppError):
    """Raised when the service is temporarily unavailable."""

    code = 503
    type = "service_unavailable"
    message = T("health.database_unavailable")
