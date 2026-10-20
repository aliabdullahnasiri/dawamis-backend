from app.schemas.auth.data.auth import LoginData
from app.schemas.auth.data.two_factor import RecoveryCodesData, TwoFactorSetupData

from app.schemas.base import BaseResponseModel


class TwoFactorSetupResponse(BaseResponseModel[TwoFactorSetupData]):
    """
    Response containing the two-factor authentication setup details,
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
