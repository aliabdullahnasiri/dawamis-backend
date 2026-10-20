from .base import BaseTwoFactorRequest


class OTPEnableRequest(BaseTwoFactorRequest):
    """
    Schema for enabling OTP authentication.
    """


class OTPVerifyRequest(BaseTwoFactorRequest):
    """
    Schema for verifying an OTP code.
    """
