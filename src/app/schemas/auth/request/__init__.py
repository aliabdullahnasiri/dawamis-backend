from .login import LoginRequest
from .registration import RegisterRequest
from .verification import ResendVerificationEmailRequest, VerifyEmailRequest
from .password import ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from .two_factor import (
    OTPEnableRequest,
    OTPVerifyRequest,
    TOTPEnableRequest,
    TOTPVerifyRequest,
    TwoFactorDisableRequest,
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "ResendVerificationEmailRequest",
    "VerifyEmailRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "TwoFactorDisableRequest",
    "OTPEnableRequest",
    "OTPVerifyRequest",
    "TOTPEnableRequest",
    "TOTPVerifyRequest",
]
