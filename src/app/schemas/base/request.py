from app.schemas.base.model import Model


class BaseRequestModel(Model):
    """
    Base schema for all API request payloads.

    Provides the common foundation for request validation
    schemas used throughout the application.
    """
