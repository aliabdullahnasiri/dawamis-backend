import re
from inspect import getmembers, ismethod
from operator import call
from typing import Self

from pydantic import BaseModel, model_validator

from app.schemas.base.meta import BaseModelMeta


class Model(BaseModel, metaclass=BaseModelMeta):

    @model_validator(mode="after")
    def _validate(self: Self) -> Self:
        pattern = re.compile(r"^_validate_(\w+)$")

        for name, method in getmembers(self, predicate=ismethod):
            match = pattern.fullmatch(name)

            if not match:
                continue

            field_name = match.group(1)

            if field_name not in self.model_fields:
                continue

            call(method, value=getattr(self, field_name))

        return self
