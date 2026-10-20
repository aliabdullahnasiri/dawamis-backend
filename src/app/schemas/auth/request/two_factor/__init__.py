from .base import BaseTwoFactorRequest, TwoFactorDisableRequest
from .otp import OTPEnableRequest, OTPVerifyRequest
from .totp import TOTPEnableRequest, TOTPVerifyRequest

__all__ = [
    "BaseTwoFactorRequest",
    "OTPEnableRequest",
    "OTPVerifyRequest",
    "TOTPEnableRequest",
    "TOTPVerifyRequest",
    "TwoFactorDisableRequest",
]
