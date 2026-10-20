from datetime import datetime
from uuid import UUID

from app.schemas.base import BaseDataModel


class SessionData(BaseDataModel):
    """
    Data representing a user session.
    """

    id: int
    uuid: UUID
    ip_address: str | None
    user_agent: str | None
    last_used_at: datetime | None
    expires_at: datetime
