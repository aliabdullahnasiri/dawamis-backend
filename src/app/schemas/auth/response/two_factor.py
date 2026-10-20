from app.schemas.auth.data.auth import LoginData
from app.schemas.auth.data.two_factor import RecoveryCodesData, TOTPSetupData
from app.schemas.base import BaseResponseModel


class TOTPSetupResponse(BaseResponseModel[TOTPSetupData]):
    """
    Response containing the TOTP setup details,
    including the QR code URL or secret key.
    """


class TwoFactorVerifyResponse(BaseResponseModel[LoginData]):
    """
    Response schema for successful 2FA verification.
    Returns final authentication tokens.
    """


class RecoveryCodesResponse(BaseResponseModel[RecoveryCodesData]):
    """
    Response containing the user's one-time recovery codes for
    two-factor authentication.
    """

    __forbid__ = True
