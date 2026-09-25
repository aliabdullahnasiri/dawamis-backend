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


class VerifyEmailRequest(BaseRequestModel):
    token: str = Field(min_length=1)


class ResendVerificationEmailRequest(BaseRequestModel):
    email: EmailStr


class ForgotPasswordRequest(BaseRequestModel):
    """
    Schema for requesting a password reset.
    """

    email: EmailStr


class ResetPasswordRequest(BaseRequestModel):
    """
    Schema for resetting a password using a token.
    """

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseRequestModel):
    """
    Schema for changing a password while authenticated.
    """

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

