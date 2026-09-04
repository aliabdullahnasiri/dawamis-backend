import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Self
from uuid import UUID

from sqlalchemy import DateTime, func, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class DeclarativeBaseMeta(type(DeclarativeBase)):
    """
    Custom metaclass that controls model behavior.
    """

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        model = super().__new__(
            cls,
            name,
            bases,
            namespace,
            **kwargs,
        )

        return model


class Base(DeclarativeBase, metaclass=DeclarativeBaseMeta):
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, default=lambda: uuid.uuid4())

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __hidden_fields__: set[str] = set()

    def to_dict(self: Self) -> dict[str, Any]:
        """
        Convert the SQLAlchemy model instance into a dictionary.

        Returns:
            A dictionary containing all mapped column values.
        """
        return {
            column.key: getattr(self, column.key)
            for column in inspect(self).mapper.column_attrs
            if column.key not in self.__hidden_fields__
        }

    def to_json(self: Self, **kwargs: Any) -> str:
        """
        Convert the SQLAlchemy model instance into a JSON string.

        Args:
            **kwargs: Additional options passed to ``json.dumps()``.

        Returns:
            A JSON representation of the model.
        """
        return json.dumps(
            self.to_dict(),
            default=self._json_serializer,
            **kwargs,
        )

    @staticmethod
    def _json_serializer(value: Any) -> str:
        """
        Serialize objects that are not natively supported by ``json``.
        """
        if isinstance(value, (UUID)):
            return f"{value}"
        elif isinstance(value, (date, datetime)):
            return value.isoformat()

        raise TypeError(
            f"Object of type {type(value).__name__} " "is not JSON serializable"
        )

    def __repr__(self: Self) -> str:
        return (
            f"<{type(self).__name__} "
            f"uuid={self.uuid!r} "
            f"object at 0x{id(self):x}>"
        )
