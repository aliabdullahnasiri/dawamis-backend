from pydantic import EmailStr, Field

from app.schemas.base import BaseRequestModel


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
