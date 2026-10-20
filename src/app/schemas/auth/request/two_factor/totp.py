from pydantic import Field
from .base import BaseTwoFactorRequest


class TOTPEnableRequest(BaseTwoFactorRequest):
    """
    Schema for enabling TOTP authentication.
    """
    code: str = Field(pattern=r"^\d{6}$")


class TOTPVerifyRequest(BaseTwoFactorRequest):
    """
    Schema for verifying a TOTP code.
    """
    pass
