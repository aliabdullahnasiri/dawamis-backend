from datetime import datetime
from uuid import UUID

from pydantic import JsonValue

from app.schemas.base.model import Model


class OrganizationData(Model):
    id: int
    uuid: UUID
    name: str
    slug: str
    is_active: bool
    owner_id: int | None
    settings: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime


class MembershipData(Model):
    id: int
    uuid: UUID
    organization_id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
