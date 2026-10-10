from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    code = 404
    type = "not_found"
    message = T("errors:not_found")


class UserNotFound(AppError):
    """Raised when a user does not exist."""

    code = 404
    type = "user_not_found"
    message = T("user:not_found")
