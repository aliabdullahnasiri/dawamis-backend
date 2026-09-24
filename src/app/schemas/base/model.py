
from pydantic import BaseModel

from app.schemas.base.meta import BaseModelMeta


class Model(BaseModel, metaclass=BaseModelMeta):
    pass
