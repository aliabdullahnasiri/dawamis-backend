from typing import Any

from pydantic import BaseModel, model_validator
from pydantic_async_validation.mixins import AsyncValidationModelMixin

from app.schemas.base.meta import BaseModelMeta


class Model(AsyncValidationModelMixin, BaseModel, metaclass=BaseModelMeta):
    """
    Core base model for all application schemas.

    Extends Pydantic's BaseModel and integrates asynchronous validation
    capabilities via AsyncValidationModelMixin and customized metaclass
    behavior via BaseModelMeta.
    """

    @model_validator(mode="before")
    @classmethod
    def _validate(cls: type[Model], values: Any) -> Any:
        """
        Internal pre-validation hook.

        Allows for custom validation logic to be executed before Pydantic's
        standard validation.
        """
        return values
