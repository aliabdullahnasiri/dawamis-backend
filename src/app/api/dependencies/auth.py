from typing import Annotated, Any, Generic, Type, TypeVar
from uuid import UUID

from fastapi import Depends

from app.core.security import (
    current_user_can,
    get_current_claims,
    get_current_refresh_token,
    get_current_token,
    get_current_user_uuid,
)
from app.models.permission import Permission

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


class CurrentUserCan:
    def __class_getitem__(cls, permissions: str | tuple) -> Annotated:
        if isinstance(permissions, str):
            permissions = (permissions,)

        return Annotated[None, Depends(current_user_can(*permissions))]
