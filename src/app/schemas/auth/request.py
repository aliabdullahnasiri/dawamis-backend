from pydantic import EmailStr, Field

from app.schemas.base import BaseRequestModel
from app.schemas.user import CreateUserRequest


class LoginRequest(BaseRequestModel):
    """
    Schema for validating user authentication credentials.

    Accepts an email address together with the user's password.
    """

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class RegisterRequest(CreateUserRequest):
    """
    Schema for the user registration request.

    Extends CreateUserRequest by adding a requirement to accept
    the terms and conditions.
    """

    accept_terms: bool


class VerifyEmailRequest(BaseRequestModel):
    """
    Schema for verifying a user's email address using a token.
    """
    token: str = Field(min_length=1)


class ResendVerificationEmailRequest(BaseRequestModel):
    """
    Schema for requesting a new email verification link.
    """
    email: EmailStr


class ForgotPasswordRequest(BaseRequestModel):
    """
    Schema for requesting a password reset.
    """

    email: EmailStr


class ResetPasswordRequest(BaseRequestModel):
    """
    Schema for resetting a password using a valid reset token.
    """

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseRequestModel):
    """
    Schema for changing a password while the user is authenticated.
    """

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class TwoFactorEnableRequest(BaseRequestModel):
    """
    Schema for enabling two-factor authentication.

    Requires a 6-digit verification code.
    """
    code: str = Field(pattern=r"^\d{6}$")


class TwoFactorVerifyRequest(BaseRequestModel):
    """
    Schema for verifying a two-factor authentication code.
    """
    code: str = Field(min_length=6, max_length=64)


class TwoFactorDisableRequest(BaseRequestModel):
    """
    Schema for disabling two-factor authentication.

    Requires the user's password and a current verification code.
    """
    password: str
    code: str = Field(min_length=6, max_length=64)
