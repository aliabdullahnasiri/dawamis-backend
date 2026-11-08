from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies.auth import CurrentActiveSession, PermissionRequired
from app.api.dependencies.db import DBSession
from app.core.exceptions import AuthorizationError
from app.core.i18n.types import T
from app.schemas.base.response import BaseResponseModel
from app.schemas.organization.data.organization import MembershipData, OrganizationData
from app.schemas.organization.request.organization import (
    AddMemberRequest,
    CreateOrganizationRequest,
    UpdateMemberRequest,
    UpdateOrganizationRequest,
)
from app.schemas.organization.response.organization import (
    MembershipResponse,
    MembershipsResponse,
    OrganizationResponse,
    OrganizationsResponse,
)
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "/{organization_uuid}/join-requests",
    response_model=BaseResponseModel[None],
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_to_join_organization(
    organization_uuid: UUID, session: CurrentActiveSession, db: DBSession
) -> BaseResponseModel[None]:
    """Queue an email asking the owner to approve the authenticated user's access."""
    await OrganizationService.request_to_join(db, session.user, organization_uuid)
    return BaseResponseModel[None](message=T("organization:join_request_queued"))


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    request: CreateOrganizationRequest, session: CurrentActiveSession, db: DBSession
) -> OrganizationResponse:
    """Create an organization and its owner membership atomically."""
    organization = await OrganizationService.create(
        db, request.name, request.slug, owner=session.user, settings=request.settings
    )
    return OrganizationResponse(data=OrganizationData.model_validate(organization))


@router.get("", response_model=OrganizationsResponse)
async def list_organizations(
    session: CurrentActiveSession,
    db: DBSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> OrganizationsResponse:
    """List organizations the current user belongs to."""
    organizations = await OrganizationService.list_for_user(
        db, session.user, offset, limit
    )
    return OrganizationsResponse(
        data=[OrganizationData.model_validate(org) for org in organizations]
    )


@router.get("/{organization_uuid}", response_model=OrganizationResponse)
async def get_organization(
    organization_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["organizations.read"],  # noqa: F821, UP037
) -> OrganizationResponse:
    """Retrieve an organization accessible to the current user."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    return OrganizationResponse(data=OrganizationData.model_validate(organization))


@router.patch("/{organization_uuid}", response_model=OrganizationResponse)
async def update_organization(
    organization_uuid: UUID,
    request: UpdateOrganizationRequest,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["organizations.update"],  # noqa: F821, UP037
) -> OrganizationResponse:
    """Update organization settings, status, or transfer ownership."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    if request.owner_id is not None and organization.owner_id != session.user_id:
        raise AuthorizationError()
    organization = await OrganizationService.update(
        db, organization, **request.model_dump(exclude_unset=True)
    )
    return OrganizationResponse(data=OrganizationData.model_validate(organization))


@router.delete("/{organization_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_uuid: UUID,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["organizations.delete"],  # noqa: F821, UP037
) -> None:
    """Delete an organization and clear its selected session contexts."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    await OrganizationService.delete(db, organization)


@router.get("/{organization_uuid}/members", response_model=MembershipsResponse)
async def list_members(
    organization_uuid: UUID,
    db: DBSession,
    _: PermissionRequired["organizations.members.read"],  # noqa: F821, UP037
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> MembershipsResponse:
    """List memberships within an accessible organization."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    members = await OrganizationService.members(db, organization.id, offset, limit)
    return MembershipsResponse(
        data=[MembershipData.model_validate(member) for member in members]
    )


@router.post(
    "/{organization_uuid}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    organization_uuid: UUID,
    request: AddMemberRequest,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["organizations.members.manage"],  # noqa: F821, UP037
) -> MembershipResponse:
    """Add an existing user to this organization."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    member = await OrganizationService.add_member(db, organization.id, request.user_id)
    return MembershipResponse(data=MembershipData.model_validate(member))


@router.patch(
    "/{organization_uuid}/members/{member_uuid}", response_model=MembershipResponse
)
async def update_member(
    organization_uuid: UUID,
    member_uuid: UUID,
    request: UpdateMemberRequest,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["organizations.members.manage"],  # noqa: F821, UP037
) -> MembershipResponse:
    """Activate or deactivate a membership, identified by its membership UUID."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    member = await OrganizationService.get_member_by_uuid(
        db, organization.id, member_uuid
    )
    member = await OrganizationService.update_member(
        db, organization, member, request.is_active
    )
    return MembershipResponse(data=MembershipData.model_validate(member))


@router.delete(
    "/{organization_uuid}/members/{member_uuid}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    organization_uuid: UUID,
    member_uuid: UUID,
    session: CurrentActiveSession,
    db: DBSession,
    _: PermissionRequired["organizations.members.manage"],  # noqa: F821, UP037
) -> None:
    """Remove a membership and its organization-specific role grants."""
    organization = await OrganizationService.get_by_uuid(db, organization_uuid)
    member = await OrganizationService.get_member_by_uuid(
        db, organization.id, member_uuid
    )
    await OrganizationService.remove_member(db, organization.id, member.user_id)
