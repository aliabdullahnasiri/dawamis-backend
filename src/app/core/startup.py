from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.redis import RedisClient


class Startup:
    """
    Handles application startup and shutdown tasks.

    Designed to be used as an asynchronous context manager to ensure that
    initialization logic is performed before the app starts and cleanup
    (like commits/rollbacks) is performed on exit.
    """
    def __init__(
        self: Self, db: AsyncSession | None = None, redis: RedisClient | None = None
    ) -> None:
        """
        Initialize the Startup manager.

        Args:
            db: Optional database session for initialization tasks.
            redis: Optional Redis client for initialization tasks.
        """
        self.db: AsyncSession | None = db
        self.redis: RedisClient | None = redis

    async def __aenter__(self: Self) -> Self:
        """
        Entry point for the asynchronous context manager.
        Performs initialization of roles and permissions if a database session is provided.
        """
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
        """
        Exit point for the asynchronous context manager.
        Commits changes if successful, otherwise rolls back the database session.
        """
        if self.db is None:
            return

        if exc_type is not None:
            await self.db.rollback()
        else:
            await self.db.commit()

    async def _init_roles(self: Self) -> None:
        """
        Internal method to initialize system roles in the database.
        """
        ...

    async def _init_permissions(self: Self) -> None:
        """
        Internal method to initialize system permissions in the database.
        """
        ...
