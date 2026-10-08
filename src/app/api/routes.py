from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi.routing import APIRoute

from app.schemas.base.model import Model


class AsyncValidationRoute(APIRoute):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        **kwargs: Any,
    ) -> None:
        @wraps(endpoint)
        async def validated_endpoint(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            for value in kwargs.values():
                if isinstance(value, Model):
                    await value.model_async_validate()

            return await endpoint(*args, **kwargs)

        super().__init__(
            path,
            validated_endpoint,
            **kwargs,
        )
