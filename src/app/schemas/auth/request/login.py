from pydantic import EmailStr, Field

from app.schemas.base import BaseRequestModel


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
