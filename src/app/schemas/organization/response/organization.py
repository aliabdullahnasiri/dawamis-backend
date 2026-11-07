from app.schemas.base.response import BaseResponseModel
from app.schemas.organization.data.organization import MembershipData, OrganizationData


class OrganizationResponse(BaseResponseModel[OrganizationData]):
    pass


class OrganizationsResponse(BaseResponseModel[list[OrganizationData]]):
    pass


class MembershipResponse(BaseResponseModel[MembershipData]):
    pass


class MembershipsResponse(BaseResponseModel[list[MembershipData]]):
    pass
