from typing import Any, Self

from pydantic_core import PydanticCustomError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.context.database import get_current_db


class Unique:
    """Validate that a field value is unique in the database.

    Args:
        field: SQLAlchemy model field to check for uniqueness.
        msg: Error message to raise when the value already exists.
    """

    def __init__(
        self: Self,
        field: InstrumentedAttribute[Any],
        msg: str,
    ) -> None:
        self.field = field
        self.msg = msg

    async def __call__(self: Self, value: Any) -> Any:
        """Validate that the given value is unique.

        Args:
            value: Value to check for uniqueness.

        Returns:
            The original value if it is unique.

        Raises:
            PydanticCustomError: If the value already exists.
        """
        db: AsyncSession = get_current_db()

        stmt = select(self.field.property.parent.class_).where(self.field == value)

        result = await db.execute(stmt)

        exists = result.scalar_one_or_none() is not None

        if exists:
            raise PydanticCustomError(
                "unique",
                "{message}",
                {
                    "message": self.msg,
                },
            )

        return value

    async def validate(self: Self, value: Any) -> None:
        """Validate the given value using the uniqueness validator.

        Args:
            value: Value to check for uniqueness.

        Raises:
            PydanticCustomError: If the value already exists.
        """
        await self(value)
