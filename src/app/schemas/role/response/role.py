from app.schemas.base.response import BaseResponseModel
from app.schemas.role.data.role import PermissionData, RoleData


class RoleResponse(BaseResponseModel[RoleData]):
    pass


class RolesResponse(BaseResponseModel[list[RoleData]]):
    pass


class PermissionsResponse(BaseResponseModel[list[PermissionData]]):
    pass
