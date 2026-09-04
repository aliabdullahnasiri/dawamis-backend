from pydantic import EmailStr, Field

from app.schemas.base import BaseRequestModel
from app.schemas.user import CreateUserRequest


class LoginRequest(BaseRequestModel):
    """
    Schema for validating user authentication credentials.

    Accepts a email address together with the
    user's password.
    """

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class RegisterRequest(CreateUserRequest):
    """
    Handles the registration of a new user account.
    """

    accept_terms: bool
