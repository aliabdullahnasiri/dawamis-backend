from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies.db import DBSession
from app.api.dependencies.oauth import OAuth2Token, RefreshToken
from app.core.i18n.types import T
from app.errors.exceptions import AuthenticationError
from app.models.user import User
from app.models.user_session import UserSession
from app.services.jwt import JWTService
from app.services.session import SessionService
from app.services.user import UserService


async def get_current_token(
    db: DBSession,
    token: OAuth2Token,
) -> str:
    """
    Validate the access token and return it.

    The token is extracted from the Authorization header
    using the Bearer authentication scheme.

    Raises:
        HTTPException: If the token is invalid, expired,
            has an invalid type.
    """
    try:
        JWTService.decode(token)

        return token

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=T("auth:invalid_token"),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_claims(
    token: str = Depends(get_current_token),
) -> dict[str, Any]:
    """
    Return the claims from the currently authenticated access token.
    """
    return JWTService.claims(token)


async def get_current_user_uuid(
    claims: dict[str, Any] = Depends(get_current_claims),
) -> UUID:
    """
    Return the authenticated user's UUID from the JWT subject claim.

    Raises:
        HTTPException: If the JWT does not contain a subject.
    """
    user_uuid = claims.get("sub")

    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=T("auth:invalid_token_identity"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UUID(user_uuid)


async def get_current_refresh_token(
    token: RefreshToken,
    db: DBSession,
) -> str:
    """
    Validate and return the current refresh token.
    """
    try:
        claims = JWTService.decode(token)

        if claims.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=T("auth:invalid_refresh_token"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        if await JWTService.is_revoked(
            token=token,
            db=db,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=T("auth:token_revoked"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=T("auth:invalid_refresh_token"),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db: DBSession, uuid: UUID = Depends(get_current_user_uuid)
) -> User | None:
    return await UserService.get_by_uuid(db, uuid)


def current_user_can(*permissions):
    def dependency(db: DBSession, user: User = Depends(get_current_user)) -> None: ...

    return dependency


async def get_current_active_session(
    db: DBSession,
    request: Request,
    user: User = Depends(get_current_user),
) -> UserSession:
    session = await SessionService.get_active_session_for_request(
        db=db,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if not session:
        raise AuthenticationError(
            message=T("auth:session_expired_or_revoked"),
            status_code=401,
        )

    return session
