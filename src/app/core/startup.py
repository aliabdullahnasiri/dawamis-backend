from typing import Self

from redis import Redis
from sqlalchemy.orm import Session


class Startup:
    def __init__(
        self: Self, db: Session | None = None, redis: Redis | None = None
    ) -> None:
        self.db: Session | None = db
        self.redis: Redis | None = redis

    def __enter__(self: Self) -> Self:
        if self.db is not None:
            self._init_roles()
            self._init_permissions()

        return self

    def __exit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self.db is None:
            return

        if exc_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

    def _init_roles(self: Self) -> None: ...

    def _init_permissions(self: Self) -> None: ...
