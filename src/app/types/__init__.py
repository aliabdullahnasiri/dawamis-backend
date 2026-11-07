from collections.abc import Awaitable, Callable
from typing import Any

type AsyncService = Callable[..., Awaitable[Any]]

type JSONValue = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)
