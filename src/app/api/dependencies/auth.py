from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request

from app.api.dependencies.db import DBSession
from app.api.dependencies.oauth import OAuth2Token, RefreshToken
from app.api.dependencies.redis import RedisClient
from app.core.exceptions import AuthenticationError
from app.core.i18n.types import T
from app.core.security.manager import SecurityManager
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth.two_factor.challenge import (
    TwoFactorChallenge,
    TwoFactorChallengeService,
)

# Singleton instance of SecurityManager to be used by FastAPI dependencies
security_manager = SecurityManager()


async def get_current_token(
    db: DBSession,
    token: OAuth2Token,
) -> str:
    """
    FastAPI dependency to validate the current access token.
    """
    return await security_manager.get_current_token(db, token)


async def get_current_claims(
    token: str = Depends(get_current_token),
) -> dict[str, Any]:
    """
    FastAPI dependency to retrieve claims from the current access token.
    """
    return await security_manager.get_current_claims(token)


async def get_current_user_uuid(
    claims: dict[str, Any] = Depends(get_current_claims),
) -> UUID:
    """
    FastAPI dependency to retrieve the authenticated user's UUID.
    """
    return await security_manager.get_current_user_uuid(claims)


async def get_current_user(
    db: DBSession, uuid: UUID = Depends(get_current_user_uuid)
) -> User | None:
    """
    FastAPI dependency to retrieve the currently authenticated User object.
    """
    return await security_manager.get_current_user(db, uuid)


def current_user_can(*permissions):
    """
    FastAPI dependency factory to check if the current user has specific permissions.
    """

    def dependency(db: DBSession, user: User = Depends(get_current_user)) -> None:
        # Logic for permission check would go here,
        # mirroring the original empty implementation
        ...

    return dependency


async def get_current_refresh_token(
    token: RefreshToken,
    db: DBSession,
) -> str:
    """
    FastAPI dependency to validate the current refresh token.
    """
    return await security_manager.get_current_refresh_token(token, db)


async def get_current_active_session(
    db: DBSession,
    request: Request,
    user: User | None = Depends(get_current_user),
) -> UserSession:
    """
    FastAPI dependency to retrieve the current active session for the authenticated user.
    """
    if user is None:
        raise AuthenticationError(
            message=T("auth:user_not_found"),
            code=401,
        )

    return await security_manager.get_current_active_session(db, request, user)


async def get_current_2fa_challenge(
    token: CurrentToken,
    redis: RedisClient,
) -> TwoFactorChallenge:
    """
    Validate the 2FA challenge token and return the challenge details.
    """
    return await TwoFactorChallengeService.validate(redis, token)


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

Current2FAChallenge = Annotated[
    TwoFactorChallenge,
    Depends(get_current_2fa_challenge),
]


CurrentUser = Annotated[User, Depends(get_current_user)]

CurrentActiveSession = Annotated[UserSession, Depends(get_current_active_session)]


class PermissionRequired:
    def __class_getitem__(cls, permissions: str | tuple) -> Annotated:
        if isinstance(permissions, str):
            permissions = (permissions,)

        return Annotated[None, Depends(current_user_can(*[p for p in permissions]))]
