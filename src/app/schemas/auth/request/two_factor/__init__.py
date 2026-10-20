from .base import BaseTwoFactorRequest, TwoFactorDisableRequest
from .totp import TOTPEnableRequest, TOTPVerifyRequest
from .otp import OTPEnableRequest, OTPVerifyRequest

__all__ = [
    "BaseTwoFactorRequest",
    "TwoFactorDisableRequest",
    "TOTPEnableRequest",
    "TOTPVerifyRequest",
    "OTPEnableRequest",
    "OTPVerifyRequest",
]
