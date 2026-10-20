from pydantic import Field

from app.schemas.base import BaseRequestModel


class BaseTwoFactorRequest(BaseRequestModel):
    """
    Base schema for all two-factor authentication requests.
    """
    code: str = Field(min_length=6, max_length=64)


class TOTPEnableRequest(BaseTwoFactorRequest):
    """
    Schema for enabling TOTP authentication.
    Requires a 6-digit verification code.
    """
    code: str = Field(pattern=r"^\d{6}$")


class OTPEnableRequest(BaseTwoFactorRequest):
    """
    Schema for enabling OTP authentication.
    """
    pass


class BaseTwoFactorVerifyRequest(BaseTwoFactorRequest):
    """
    Base schema for verifying a two-factor authentication code.
    """
    pass


class TOTPVerifyRequest(BaseTwoFactorVerifyRequest):
    """
    Schema for verifying a TOTP code.
    """
    pass


class OTPVerifyRequest(BaseTwoFactorVerifyRequest):
    """
    Schema for verifying an OTP code.
    """
    pass


class TwoFactorDisableRequest(BaseTwoFactorRequest):
    """
    Schema for disabling two-factor authentication.

    Requires the user's password and a current verification code.
    """
    password: str
