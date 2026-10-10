from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class ConflictError(AppError):
    """Raised when a request conflicts with the current resource state."""

    code = 409
    type = "conflict"
    message = T("errors:conflict")
