from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from app.core.exceptions import AppError

F = TypeVar("F", bound=Callable[..., Any])


def handle_exception(
    exception: type[Exception],
    *,
    _raise: type[AppError],
) -> Callable[[F], F]:
    """
    A decorator factory that converts specific exceptions into defined application errors.

    If the wrapped function raises the specified 'exception', it is caught and
    re-raised as the provided '_raise' application error. Application errors
    (AppError) are passed through unchanged.

    Args:
        exception: The exception type to intercept.
        _raise: The AppError subclass to raise instead.

    Returns:
        A decorator that wraps the target function.
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
