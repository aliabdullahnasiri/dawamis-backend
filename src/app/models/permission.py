from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.session import Session

from app.api.dependencies.db import DBSession
from app.core.config import settings
from app.core.context.database import get_current_db
from app.extensions.redis import redis
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.associations import RolePermission
    from app.models.role import Role


class Permission(Base):
    """
    Represents a permission that can be assigned to one or more roles.
    """

    __tablename__ = "permissions"
    __redis_key__ = "app:permissions"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=False,
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        viewonly=True,
    )
