from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends

from app.core.security import (
    current_user_can,
    get_current_active_session,
    get_current_claims,
    get_current_refresh_token,
    get_current_token,
    get_current_user,
    get_current_user_uuid,
)
from app.models.user import User
from app.models.user_session import UserSession

CurrentToken = Annotated[
    str,
    Depends(get_current_token),
]

CurrentRefreshToken = Annotated[
    str,
    Depends(get_current_refresh_token),
]

CurrentClaims = Annotated[
    dict[str, Any],
    Depends(get_current_claims),
]

CurrentUserUUID = Annotated[
    UUID,
    Depends(get_current_user_uuid),
]

CurrentUser = Annotated[User, Depends(get_current_user)]

CurrentActiveSession = Annotated[UserSession, Depends(get_current_active_session)]


class PermissionRequired:
    def __class_getitem__(cls, permissions: str | tuple) -> Annotated:
        if isinstance(permissions, str):
            permissions = (permissions,)

        return Annotated[None, Depends(current_user_can(*[p for p in permissions]))]
