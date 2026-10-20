from datetime import date

from pydantic import EmailStr, Field

from app.core.i18n.types import T
from app.models.user import User
from app.schemas.base import BaseRequestModel
from app.schemas.validators.unique import Unique


class BaseUserRequest(BaseRequestModel):
    """
    BaseUser schema containing common user fields.

    This schema is inherited by user creation and update
    schemas to provide consistent validation for personal
    information, username, email, and birthday.
    """

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    middle_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    user_name: str

    email: EmailStr

    birthday: date | None = None
