from app.schemas.base import BaseResponseModel
from app.schemas.user import UserData


class RegisterResponse(BaseResponseModel[UserData]):
    """
    Schema for the successful registration response.
    Returns the created user's basic data.
    """
