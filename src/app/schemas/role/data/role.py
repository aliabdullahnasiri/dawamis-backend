from datetime import datetime
from uuid import UUID

from app.schemas.base.model import Model


class RoleData(Model):
    id: int
    uuid: UUID
    organization_id: int
    name: str
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class PermissionData(Model):
    id: int
    uuid: UUID
    name: str
    description: str | None
