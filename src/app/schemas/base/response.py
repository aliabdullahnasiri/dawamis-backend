from typing import Generic, TypeVar

from app.schemas.base.model import Model

T = TypeVar("T")


class BaseResponseModel(Model, Generic[T]):
    """
    Base schema for all API response payloads.

    Provides common configuration and structure for
    response schemas returned by the application.
    """

    message: str | None = None
    success: bool = True
    data: T | None = None
