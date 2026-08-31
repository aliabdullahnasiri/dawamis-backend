from app.schemas.base.model import Model


class BaseDataModel(Model):
    """
    Base Pydantic model for reusable application data.

    Provides a common foundation for data schemas that are
    shared across API requests, responses, and other
    application components.
    """
