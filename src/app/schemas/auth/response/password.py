from app.schemas.base import BaseResponseModel


class PasswordResetResponse(BaseResponseModel[None]):
    """
    Response schema for successful password management operations
    (e.g., reset request or password update).
    """
