from typing import Annotated, Any

from fastapi import Depends

from app.core.security import (
    get_current_claims,
    get_current_refresh_token,
    get_current_token,
    get_current_user_uuid,
)

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
    str,
    Depends(get_current_user_uuid),
]
