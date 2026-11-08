from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from app.schemas.base.request import BaseRequestModel

RoleName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
PermissionName = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class CreateRoleRequest(BaseRequestModel):
    __extra__ = "forbid"
    name: RoleName
    description: str | None = Field(default=None, max_length=255)


class UpdateRoleRequest(BaseRequestModel):
    __extra__ = "forbid"
    name: RoleName | None = None
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def reject_null_name(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class SetRolePermissionsRequest(BaseRequestModel):
    __extra__ = "forbid"
    permissions: list[PermissionName] = Field(max_length=500)


class SetMemberRolesRequest(BaseRequestModel):
    __extra__ = "forbid"
    role_uuids: list[UUID] = Field(max_length=100)
