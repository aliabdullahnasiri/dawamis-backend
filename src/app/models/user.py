from datetime import date
from typing import TYPE_CHECKING, Any

import bcrypt
from sqlalchemy import Date, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.associations import UserRole
    from app.models.permission import Permission
    from app.models.role import Role


class User(Base):
    __tablename__ = "users"

    __hidden_fields__ = {"password_hash"}

    first_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    middle_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    user_name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    birthday: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "user_name"),
        UniqueConstraint("email", name="uc_user_email"),
        UniqueConstraint("user_name", name="uc_user_username"),
    )

    @property
    def permissions(self) -> list["Permission"]:
        """
        Return all permissions granted to this user through their roles.
        """
        permissions: list["Permission"] = []

        for role in self.roles:
            permissions.extend(role.permissions)

        return permissions

    def set_password(self, password: str) -> None:
        password_bytes = password.encode("utf-8")

        self.password_hash = bcrypt.hashpw(
            password_bytes,
            bcrypt.gensalt(),
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )
