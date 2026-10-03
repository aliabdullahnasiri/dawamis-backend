from __future__ import annotations

from typing import Any

from sqlalchemy import JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.enums.security import SecurityEventType
from app.models.base import Base


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
