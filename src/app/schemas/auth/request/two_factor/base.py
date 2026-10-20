from pydantic import Field

from app.schemas.base import BaseRequestModel


class BaseTwoFactorRequest(BaseRequestModel):
    """
    Base schema for all two-factor authentication requests.
    """
    code: str = Field(min_length=6, max_length=64)


class TwoFactorDisableRequest(BaseTwoFactorRequest):
    """
    Schema for disabling two-factor authentication.
    """
    password: str
