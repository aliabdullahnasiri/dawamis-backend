from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class ValidationError(AppError):
    """Raised when business-level validation fails."""

    code = 422
    type = "validation_error"
    message = T("validation:failed")
