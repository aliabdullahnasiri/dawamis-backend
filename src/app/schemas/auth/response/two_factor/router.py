from app.schemas.auth.data.auth import LoginData
from app.schemas.auth.data.two_factor.common import RecoveryCodesData
from app.schemas.auth.data.two_factor.otp import OTPSetupData
from app.schemas.auth.data.two_factor.totp import TOTPSetupData
from app.schemas.base import BaseResponseModel


class TOTPSetupResponse(BaseResponseModel[TOTPSetupData]):
    """
    Response containing the TOTP setup details.
    """


class OTPSetupResponse(BaseResponseModel[OTPSetupData]):
    """
    Response containing the OTP setup details.
    """


class TwoFactorVerifyResponse(BaseResponseModel[LoginData]):
    """
    Response schema for successful 2FA verification.
    """


class RecoveryCodesResponse(BaseResponseModel[RecoveryCodesData]):
    """
    Response containing recovery codes.
    """
