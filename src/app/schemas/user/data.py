from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr

from app.schemas.base import BaseDataModel


class UserData(BaseDataModel):
    uuid: UUID
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    user_name: str
    email: EmailStr
    birthday: date | None
    created_at: datetime
    updated_at: datetime
