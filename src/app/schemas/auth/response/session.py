from app.schemas.auth.data.session import SessionData

from app.schemas.base import BaseResponseModel


class SessionsResponse(BaseResponseModel[list[SessionData]]):
    """
    Response schema for listing all active user sessions.
    """


class RevokeSessionResponse(BaseResponseModel[None]):
    """
    Response schema for successful session revocation.
    """
