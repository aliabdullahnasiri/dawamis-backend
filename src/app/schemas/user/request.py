from datetime import date
from typing import Annotated

from pydantic import EmailStr, Field
from pydantic.functional_validators import AfterValidator

from app.core.i18n.types import T
from app.models.user import User
from app.schemas.base import BaseRequestModel
from app.schemas.types import Unique


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

    user_name: Annotated[
        str,
        AfterValidator(Unique(User, "user_name", T("auth.username_exists"))),
    ]

    email: Annotated[
        EmailStr,
        AfterValidator(Unique(User, "email", T("auth.email_exists"))),
    ]

    birthday: date | None = None


class GetUserRequest(BaseUserRequest):
    pass


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
