from app.core.exceptions.base import AppError
from app.core.i18n.types import T


class RateLimitError(AppError):
    """Raised when a rate limit is exceeded."""

    code = 429
    type = "rate_limit_exceeded"
    message = T("auth:too_many_attempts")
