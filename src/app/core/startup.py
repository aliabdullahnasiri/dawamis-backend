import re
from typing import Self

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import Base
from app.models.permission import Permission
from app.models.role import Role


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

    def _init_roles(self: Self) -> None:
        if self.db is None:
            return

        for role_name in settings.DEFAULT_ROLES:
            role = self.db.scalar(select(Role).where(Role.name == role_name))

            if role is None:
                self.db.add(Role(name=role_name))

    def _init_permissions(self: Self) -> None:
        for name in Permission.names:
            if self.db and self.redis:
                try:
                    p: Permission | None = (
                        self.db.query(Permission)
                        .filter(Permission.name == name)
                        .scalar()
                    )

                    if p is None:
                        p = Permission()

                        p.name = name
                        p.code = 0x1 << self.db.query(Permission).count()

                        self.db.add(p)

                    self.db.commit()

                    self.redis.hset(Permission.__redis_key__, p.name, p.code)

                except ValueError as err:
                    print(err)
