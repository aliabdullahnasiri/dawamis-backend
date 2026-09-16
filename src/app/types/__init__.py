from collections.abc import Awaitable, Callable
from typing import Any

type AsyncService = Callable[..., Awaitable[Any]]
