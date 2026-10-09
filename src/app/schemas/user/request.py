from datetime import date
from typing import Self

from pydantic import EmailStr, Field
from pydantic_async_validation.validators import async_field_validator

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


class CreateUserRequest(BaseUserRequest):
    """
    Schema for validating user creation data.

    Extends the base user fields with a password that is
    validated before the user is created.
    """

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @async_field_validator("email")
    async def _validate_email(self: Self) -> None:
        await Unique(User.email, T("email:email_already_exists")).validate(self.email)

    @async_field_validator("user_name")
    async def _validate_user_name(self: Self) -> None:
        await Unique(
            User.user_name,
            T("user_name:user_name_already_exists"),
        ).validate(self.user_name)


class UpdateUserRequest(BaseUserRequest):
    pass
