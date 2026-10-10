from typing import Self

from app.core.i18n.types import T


class AppError(Exception):
    """Base exception for application-level errors."""

    code: int = 500
    type: str = "internal_error"
    message: str = T("errors:internal_error")

    def __init__(
        self: Self,
        message: str | None = None,
        code: int | None = None,
        type: str | None = None,
    ) -> None:
        self.code = code if code is not None else self.code
        self.type = type if type is not None else self.type
        self.message = message if message is not None else self.message
