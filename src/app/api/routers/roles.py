from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies.auth import CurrentActiveSession, PermissionRequired
from app.api.dependencies.db import DBSession
from app.schemas.role.data.role import PermissionData, RoleData
from app.schemas.role.request.role import (
    CreateRoleRequest,
    SetMemberRolesRequest,
    SetRolePermissionsRequest,
    UpdateRoleRequest,
)
from app.schemas.role.response.role import (
    PermissionsResponse,
    RoleResponse,
    RolesResponse,
)
from app.services.organization import OrganizationService
from app.services.permission import PermissionService
from app.services.role import RoleService

router = APIRouter(
    prefix="/organizations/{organization_uuid}", tags=["Organization RBAC"]
)


@router.get("/roles", response_model=RolesResponse)
async def list_roles(
    organization_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["roles:read"],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> RolesResponse:
    """List roles belonging to this organization."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    roles = await RoleService.list(db, organization.id, offset, limit)
    return RolesResponse(data=[RoleData.model_validate(role) for role in roles])


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    organization_uuid: UUID,
    request: CreateRoleRequest,
    db: DBSession,
    _: PermissionRequired["roles:create"],
) -> RoleResponse:
    """Create a custom role with no initial permissions."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    role = await RoleService.create(
        db, organization.id, request.name, request.description
    )
    return RoleResponse(data=RoleData.model_validate(role))


@router.get("/roles/{role_uuid}", response_model=RoleResponse)
async def get_role(
    organization_uuid: UUID,
    role_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["roles:read"],
) -> RoleResponse:
    """Retrieve a role only within the URL's organization."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    role = await RoleService.get(db, organization.id, role_uuid)
    return RoleResponse(data=RoleData.model_validate(role))


@router.patch("/roles/{role_uuid}", response_model=RoleResponse)
async def update_role(
    organization_uuid: UUID,
    role_uuid: UUID,
    request: UpdateRoleRequest,
    db: DBSession,
    _: PermissionRequired["roles:update"],
) -> RoleResponse:
    """Update a custom role's name or description."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    role = await RoleService.update(
        db, organization.id, role_uuid, request.model_dump(exclude_unset=True)
    )
    return RoleResponse(data=RoleData.model_validate(role))


@router.delete("/roles/{role_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    organization_uuid: UUID,
    role_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["roles:delete"],
) -> None:
    """Delete a custom role and revoke all of its grants."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    await RoleService.delete(db, organization.id, role_uuid)


@router.get("/permissions", response_model=PermissionsResponse)
async def list_permissions(
    organization_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["permissions:read"],
) -> PermissionsResponse:
    """List available definitions; listing does not assign any permissions."""
    permissions = await PermissionService.list_definitions(db)
    return PermissionsResponse(
        data=[PermissionData.model_validate(p) for p in permissions]
    )


@router.get("/roles/{role_uuid}/permissions", response_model=PermissionsResponse)
async def get_role_permissions(
    organization_uuid: UUID,
    role_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["roles:read"],
) -> PermissionsResponse:
    """List permissions granted by an organization role."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    permissions = await RoleService.permissions(db, organization.id, role_uuid)
    return PermissionsResponse(
        data=[PermissionData.model_validate(p) for p in permissions]
    )


@router.put("/roles/{role_uuid}/permissions", response_model=PermissionsResponse)
async def set_role_permissions(
    organization_uuid: UUID,
    role_uuid: UUID,
    request: SetRolePermissionsRequest,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["roles:permissions:update"],
) -> PermissionsResponse:
    """Replace grants atomically; an empty list clears them."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    permissions = await RoleService.set_permissions(
        db, organization.id, role_uuid, request.permissions, session.user_id
    )
    return PermissionsResponse(
        data=[PermissionData.model_validate(p) for p in permissions]
    )


@router.get("/members/{member_uuid}/roles", response_model=RolesResponse)
async def get_member_roles(
    organization_uuid: UUID,
    member_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["roles:read"],
) -> RolesResponse:
    """List roles assigned to an organization membership."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    roles = await RoleService.member_roles(db, organization.id, member_uuid)
    return RolesResponse(data=[RoleData.model_validate(role) for role in roles])


@router.put("/members/{member_uuid}/roles", response_model=RolesResponse)
async def set_member_roles(
    organization_uuid: UUID,
    member_uuid: UUID,
    request: SetMemberRolesRequest,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["roles:assign"],
) -> RolesResponse:
    """Replace membership roles atomically; an empty list revokes all roles."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    roles = await RoleService.set_member_roles(
        db, organization.id, member_uuid, request.role_uuids, session.user_id
    )
    return RolesResponse(data=[RoleData.model_validate(role) for role in roles])
