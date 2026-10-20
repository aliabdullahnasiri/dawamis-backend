from pydantic import Field

from app.schemas.base import BaseRequestModel


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
