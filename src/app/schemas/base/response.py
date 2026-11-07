from app.schemas.base.model import Model


class BaseResponseModel[T](Model):
    """
    Base schema for all API response payloads.

    Provides common configuration and structure for
    response schemas returned by the application.
    """

    __exclude_none__ = True

    message: str | None = None
    success: bool = True
    data: T | None = None
