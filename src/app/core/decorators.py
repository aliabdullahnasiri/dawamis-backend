from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from app.core.i18n.types import T
from app.errors.exceptions import AppError

F = TypeVar("F", bound=Callable[..., Any])


def handle_exception(
    exception: type[Exception],
    *,
    _raise: type[AppError],
) -> Callable[[F], F]:
    """
    Convert an exception into an application error.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)

            except AppError:
                raise

            except exception as exc:
                raise _raise() from exc

        return wrapper  # type: ignore[return-value]

    return decorator
