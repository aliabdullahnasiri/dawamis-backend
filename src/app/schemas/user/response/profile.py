from app.schemas.base import BaseResponseModel
from app.schemas.user.data.profile import UserData


class GetUserResponse(BaseResponseModel[UserData]):
    """
    Response schema for retrieving a single user's profile.
    """


class CreateUserResponse(BaseResponseModel[UserData]):
    """
    Response schema for the successful creation of a new user.
    """
