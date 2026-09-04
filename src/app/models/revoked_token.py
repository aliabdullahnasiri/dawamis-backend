from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RevokedToken(Base):
    """
    Stores revoked JWT token identifiers.
    """

    __tablename__ = "revoked_tokens"

    __ownership__ = False

    jti: Mapped[UUID] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
