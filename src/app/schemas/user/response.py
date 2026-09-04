from app.schemas.base import BaseResponseModel
from app.schemas.user.data import UserData


class GetUserResponse(BaseResponseModel[UserData]):
    pass


class CreateUserResponse(BaseResponseModel[UserData]):
    pass
