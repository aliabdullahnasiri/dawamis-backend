from pydantic_core import PydanticCustomError

from app.core.context.database import get_current_db


class Unique:
    """Validate that a value is unique in the database."""

    def __init__(self, model, field, msg):
        self.model = model
        self.field = field
        self.msg = msg

    def __call__(self, value):
        db = get_current_db()

        exists = (
            db.query(self.model)
            .filter(getattr(self.model, self.field) == value)
            .first()
        )

        if exists:
            raise PydanticCustomError(
                "unique", self.msg, {"field": self.field, "status_code": 409}
            )

        return value
