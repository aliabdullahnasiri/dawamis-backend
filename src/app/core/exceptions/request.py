from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class BadRequestError(AppError):
    """Raised when a request is invalid."""

    code = 400
    type = "bad_request"
    message = T("request:bad_request")
