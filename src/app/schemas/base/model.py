from typing import Any, Type

from pydantic import BaseModel, model_validator
from pydantic_async_validation.mixins import AsyncValidationModelMixin

from app.schemas.base.meta import BaseModelMeta


class Model(AsyncValidationModelMixin, BaseModel, metaclass=BaseModelMeta):

    @model_validator(mode="before")
    @classmethod
    def _validate(cls: Type[Model], values: Any) -> Any:
        return values
