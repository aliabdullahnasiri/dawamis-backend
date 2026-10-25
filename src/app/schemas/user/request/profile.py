from datetime import date
from typing import Self

from pydantic import EmailStr, Field
from pydantic_async_validation.validators import async_field_validator

from app.core.i18n.types import T
from app.models.user import User
from app.schemas.base import BaseRequestModel
from app.schemas.validators.unique import Unique

from .base import BaseUserRequest


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
        """
        Ensure the email address is unique across all users.
        """
        await Unique(User.email, T("email:email_already_exists")).validate(self.email)

    @async_field_validator("user_name")
    async def _validate_user_name(self: Self) -> None:
        """
        Ensure the username is unique across all users.
        """
        await Unique(
            User.user_name,
            T("user_name:user_name_already_exists"),
        ).validate(self.user_name)


class UpdateUserRequest(BaseUserRequest):
    """
    Schema for validating user profile update data.

    Allows updating personal information, username, email, and birthday.
    All fields are optional to support PATCH requests.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    middle_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    user_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None)
    birthday: date | None = None

    @async_field_validator("email")
    async def _validate_email(self: Self) -> None:
        """
        Ensure the email address is unique across all users.
        Note: Exclusion of the current user is handled in the service layer.
        """
        if self.email:
            await Unique(User.email, T("email:email_already_exists")).validate(
                self.email
            )

    @async_field_validator("user_name")
    async def _validate_user_name(self: Self) -> None:
        """
        Ensure the username is unique across all users.
        Note: Exclusion of the current user is handled in the service layer.
        """
        if self.user_name:
            await Unique(
                User.user_name,
                T("user_name:user_name_already_exists"),
            ).validate(self.user_name)


class UpdateEmailRequest(BaseRequestModel):
    """
    Schema for updating the user's email address.
    """

    email: EmailStr = Field(...)

    @async_field_validator("email")
    async def _validate_email(self: Self) -> None:
        if self.email:
            await Unique(User.email, T("email:email_already_exists")).validate(
                self.email
            )


class UpdateUsernameRequest(BaseRequestModel):
    """
    Schema for updating the user's username.
    """

    user_name: str = Field(..., min_length=1, max_length=50)

    @async_field_validator("user_name")
    async def _validate_user_name(self: Self) -> None:
        if self.user_name:
            await Unique(
                User.user_name,
                T("user_name:user_name_already_exists"),
            ).validate(self.user_name)
