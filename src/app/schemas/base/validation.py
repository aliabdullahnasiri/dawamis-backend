from inspect import Parameter, Signature
from typing import Annotated, Any, TypeVar

from fastapi import Depends

from app.schemas.base.model import Model

T = TypeVar("T", bound=Model)


class AsyncValidated:
    def __class_getitem__(cls, model: type[T]) -> Any:

        async def dependency(data: T) -> T:
            await data.model_async_validate()
            return data

        dependency.__annotations__["data"] = model
        dependency.__annotations__["return"] = model

        dependency.__signature__ = Signature(
            [
                Parameter(
                    "data",
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=model,
                )
            ]
        )

        return Annotated[
            model,
            Depends(dependency),
        ]
