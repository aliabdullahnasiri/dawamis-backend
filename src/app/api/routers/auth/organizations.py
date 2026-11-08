from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies.auth import CurrentActiveSession, CurrentOrganization
from app.api.dependencies.db import DBSession
from app.schemas.organization.data.organization import OrganizationData
from app.schemas.organization.response.organization import OrganizationResponse
from app.services.organization import OrganizationService

router = APIRouter()


@router.post(
    "/organizations/{organization_uuid}/select", response_model=OrganizationResponse
)
async def select_organization(
    organization_uuid: UUID, session: CurrentActiveSession, db: DBSession
) -> OrganizationResponse:
    """Select an active organization for subsequent requests on this session."""
    organization = await OrganizationService.select(db, session, organization_uuid)
    return OrganizationResponse(data=OrganizationData.model_validate(organization))


@router.get("/organization", response_model=OrganizationResponse)
async def current_organization(
    organization: CurrentOrganization,
) -> OrganizationResponse:
    """Return the selected organization after checking its current membership."""
    return OrganizationResponse(data=OrganizationData.model_validate(organization))
