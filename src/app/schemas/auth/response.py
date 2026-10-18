from app.schemas.auth.data import (
    LoginData,
    RecoveryCodesData,
    RefreshData,
    SessionData,
    TwoFactorSetupData,
)
from app.schemas.base import BaseResponseModel
from app.schemas.user.data import UserData


class LoginResponse(BaseResponseModel[LoginData]):
    """
    Schema for the successful login response.
    Contains authentication tokens and user session details.
    """


class RegisterResponse(BaseResponseModel[UserData]):
    """
    Schema for the successful registration response.
    Returns the created user's basic data.
    """


class LogoutResponse(BaseResponseModel[None]):
    """
    Response schema for successful user logout.
    """


class RefreshResponse(BaseResponseModel[RefreshData]):
    """
    Response schema for successful access-token refresh.
    """


class EmailVerificationResponse(BaseResponseModel[None]):
    """
    Response schema for successful email verification.
    """


class ResendVerificationEmailResponse(BaseResponseModel[None]):
    """
    Response schema for successfully requesting a new verification email.
    """


class PasswordResetResponse(BaseResponseModel[None]):
    """
    Response schema for successful password management operations
    (e.g., reset request or password update).
    """


class SessionsResponse(BaseResponseModel[list[SessionData]]):
    """
    Response schema for listing all active user sessions.
    """


class RevokeSessionResponse(BaseResponseModel[None]):
    """
    Response schema for successful session revocation.
    """


class TwoFactorSetupResponse(BaseResponseModel[TwoFactorSetupData]):
    """
    Response containing the two-factor authentication setup details,
    including the QR code URL or secret key.
    """


class RecoveryCodesResponse(BaseResponseModel[RecoveryCodesData]):
    """
    Response containing the user's one-time recovery codes for
    two-factor authentication.
    """

    __forbid__ = True
