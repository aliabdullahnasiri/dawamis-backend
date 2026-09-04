from app.schemas.auth.data import LoginData, RefreshData
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
