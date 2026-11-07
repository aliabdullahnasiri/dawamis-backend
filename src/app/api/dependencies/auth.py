from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request

from app.api.dependencies.db import DBSession
from app.api.dependencies.oauth import OAuth2Token, RefreshToken
from app.api.dependencies.redis import RedisClient
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.i18n.types import T
from app.core.security.manager import SecurityManager
from app.models.organization import Organization
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth.jwt import JWTService
from app.services.auth.two_factor.challenge import (
    TwoFactorChallenge,
    TwoFactorChallengeService,
)
from app.services.organization import OrganizationService

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
    token: Annotated[str, Depends(get_current_token)],
) -> dict[str, Any]:
    """
    FastAPI dependency to retrieve claims from the current access token.
    """
    return await security_manager.get_current_claims(token)


async def get_current_user_uuid(
    claims: Annotated[dict[str, Any], Depends(get_current_claims)],
) -> UUID:
    """
    FastAPI dependency to retrieve the authenticated user's UUID.
    """
    return await security_manager.get_current_user_uuid(claims)


async def get_current_user(
    db: DBSession, uuid: Annotated[UUID, Depends(get_current_user_uuid)]
) -> User | None:
    """
    FastAPI dependency to retrieve the currently authenticated User object.
    """
    return await security_manager.get_current_user(db, uuid)


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
    token: Annotated[str, Depends(get_current_token)],
    user: Annotated[User | None, Depends(get_current_user)],
) -> UserSession:
    """
    FastAPI dependency to retrieve the current active session for the authenticated user.
    """
    if JWTService.claims(token).get("type") != "access" or await JWTService.is_revoked(
        token, db
    ):
        raise AuthenticationError(code=401)
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


async def get_current_refresh_session(
    db: DBSession,
    request: Request,
    token: CurrentRefreshToken,
) -> UserSession:
    """Resolve an active device session using a validated refresh token."""
    claims = await security_manager.get_current_claims(token)
    uuid = await security_manager.get_current_user_uuid(claims)
    user = await security_manager.get_current_user(db, uuid)
    if user is None:
        raise AuthenticationError(message=T("auth:user_not_found"), code=401)
    return await security_manager.get_current_active_session(db, request, user)


async def get_current_organization(
    db: DBSession, session: CurrentActiveSession
) -> Organization:
    """Resolve session context and revalidate tenant access on every request."""
    if session.organization_id is None:
        raise AuthorizationError(message=T("organization:selection_required"))
    organization = await OrganizationService.authorize(
        db, session.user, session.organization_id
    )
    if not organization.is_active:
        raise AuthorizationError()
    return organization


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


CurrentRefreshSession = Annotated[UserSession, Depends(get_current_refresh_session)]


CurrentOrganization = Annotated[Organization, Depends(get_current_organization)]


def current_user_can(*permissions: str):
    """Require all named permissions in the selected organization, denying by default."""

    async def dependency(
        db: DBSession, session: CurrentActiveSession, organization: CurrentOrganization
    ) -> None:
        await OrganizationService.require_permissions(
            db, session.user_id, organization.id, permissions
        )

    return dependency


class PermissionRequired:
    def __class_getitem__(cls, permissions: str | tuple) -> Annotated:
        if isinstance(permissions, str):
            permissions = (permissions,)

        return Annotated[None, Depends(current_user_can(*[p for p in permissions]))]
