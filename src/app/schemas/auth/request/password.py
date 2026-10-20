from pydantic import EmailStr, Field

from app.schemas.base import BaseRequestModel


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
