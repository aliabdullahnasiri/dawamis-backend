from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.security import SecurityEventType
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User

class SecurityEvent(Base):
    __tablename__ = "security_events"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[SecurityEventType] = mapped_column(
        SAEnum(
            SecurityEventType,
            name="security_event_type",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="security_events",
    )
