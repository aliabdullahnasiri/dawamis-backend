from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.associations.organization_user import OrganizationUser
    from app.models.branch import Branch


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Nullable for legacy organizations; API-created organizations always have an owner.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    settings: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), default=dict, nullable=False
    )

    memberships: Mapped[list[OrganizationUser]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    branches: Mapped[list[Branch]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
