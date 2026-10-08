import re
from inspect import getmembers, isawaitable, ismethod
from operator import call
from typing import Self

from pydantic import BaseModel
from pydantic_async_validation.mixins import AsyncValidationModelMixin
from pydantic_async_validation.validators import async_model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError, ValidationError

from app.schemas.base.meta import BaseModelMeta


class Model(AsyncValidationModelMixin, BaseModel, metaclass=BaseModelMeta):

    @async_model_validator(mode="after")
    async def _async_validate(self: Self) -> Self:
        pattern = re.compile(r"^_validate_(\w+)$")

        for name, method in getmembers(self, predicate=ismethod):
            match = pattern.fullmatch(name)

            if not match:
                continue

            field_name = match.group(1)

            if field_name not in self.model_fields:
                continue

            try:
                result = call(
                    method,
                    value=getattr(self, field_name),
                )

                if isawaitable(result):
                    await result

            except PydanticCustomError:
                raise

        return self
