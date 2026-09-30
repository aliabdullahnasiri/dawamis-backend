from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

type AsyncService = Callable[..., Awaitable[Any]]

JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)
