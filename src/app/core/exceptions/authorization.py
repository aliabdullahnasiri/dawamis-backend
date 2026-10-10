from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class AuthorizationError(AppError):
    """Raised when a user lacks permission to perform an action."""

    code = 403
    type = "authorization_error"
    message = T("auth:permission_denied")
