from app.schemas.auth.data.auth import LoginData, RefreshData

from app.schemas.base import BaseResponseModel


class LoginResponse(BaseResponseModel[LoginData]):
    """
    Schema for the successful login response.
    Contains authentication tokens and user session details.
    """


class LogoutResponse(BaseResponseModel[None]):
    """
    Response schema for successful user logout.
    """


class RefreshResponse(BaseResponseModel[RefreshData]):
    """
    Response schema for successful access-token refresh.
    """
