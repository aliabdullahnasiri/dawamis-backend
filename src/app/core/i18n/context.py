from contextvars import ContextVar

from app.core.config import settings

locale_context: ContextVar[str] = ContextVar(
    "locale",
    default=settings.DEFAULT_LANGUAGE,
)
