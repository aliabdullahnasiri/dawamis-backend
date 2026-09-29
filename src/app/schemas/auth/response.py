from typing import List
from app.schemas.auth.data import LoginData, RefreshData, SessionData
from app.schemas.base import BaseResponseModel
from app.schemas.user.data import UserData


class LoginResponse(BaseResponseModel[LoginData]):
    """
    Schema for the successful login response.
    """


class RegisterResponse(BaseResponseModel[UserData]):
    """
    Schema for the successful registration response.
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
    pass


class ResendVerificationEmailResponse(BaseResponseModel[None]):
    pass


class PasswordResetResponse(BaseResponseModel[None]):
    """
    Response schema for password management operations.
    """


class SessionsResponse(BaseResponseModel[List[SessionData]]):
    """
    Response schema for listing user sessions.
    """


class RevokeSessionResponse(BaseResponseModel[None]):
    """
    Response schema for successful session revocation.
    """
