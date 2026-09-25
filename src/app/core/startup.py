from typing import Self

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession


class Startup:
    def __init__(
        self: Self, db: AsyncSession | None = None, redis: Redis | None = None
    ) -> None:
        self.db: AsyncSession | None = db
        self.redis: Redis | None = redis

    async def __aenter__(self: Self) -> Self:
        if self.db is not None:
            await self._init_roles()
            await self._init_permissions()

        return self

    async def __aexit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self.db is None:
            return

        if exc_type is not None:
            await self.db.rollback()
        else:
            await self.db.commit()

    async def _init_roles(self: Self) -> None: ...

    async def _init_permissions(self: Self) -> None: ...
