from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict

from app.schemas.base.meta import BaseModelMeta


class Model(BaseModel, metaclass=BaseModelMeta):
    pass
