from typing import Any
from uuid import UUID

from fastapi import Request

from app.api.dependencies.db import DBSession
from app.core.exceptions import AuthenticationError, TokenError, TokenIdentityError, TokenRevokedError, RefreshTokenError
from app.core.i18n.types import T
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth.jwt import JWTService
from app.services.auth.session import SessionService
from app.services.user import UserService


class SecurityManager:
    """
    Handles security-related operations including token validation,
    user retrieval, and session management.
    """

    async def get_current_token(
        self,
        db: DBSession,
        token: str,
    ) -> str:
        """
        Validate the access token and return it.

        Args:
            db: The database session.
            token: The JWT access token to validate.

        Returns:
            The validated access token.

        Raises:
            TokenError: If the token is invalid, expired, or has an incorrect type.
        """
        try:
            JWTService.decode(token)
            return token
        except TokenError:
            raise
        except Exception:
            raise TokenError()

    async def get_current_claims(
        self,
        token: str,
    ) -> dict[str, Any]:
        """
        Return the claims from the currently authenticated access token.

        Args:
            token: The validated JWT access token.

        Returns:
            A dictionary containing the token claims.
        """
        return JWTService.claims(token)

    async def get_current_user_uuid(
        self,
        claims: dict[str, Any],
    ) -> UUID:
        """
        Return the authenticated user's UUID from the JWT subject claim.

        Args:
            claims: The claims extracted from the access token.

        Returns:
            The UUID of the authenticated user.

        Raises:
            TokenIdentityError: If the JWT does not contain a subject ('sub') claim.
        """
        user_uuid = claims.get("sub")
        if not user_uuid:
            raise TokenIdentityError()
        return UUID(user_uuid)

    async def get_current_refresh_token(
        self,
        token: str,
        db: DBSession,
    ) -> str:
        """
        Validate and return the current refresh token.

        Args:
            token: The refresh token to validate.
            db: The database session.

        Returns:
            The validated refresh token.

        Raises:
            RefreshTokenError: If the token is not a refresh token or is otherwise invalid.
            TokenRevokedError: If the refresh token has been revoked.
        """
        try:
            claims = JWTService.decode(token)
            if claims.get("type") != "refresh":
                raise RefreshTokenError()
            if await JWTService.is_revoked(token=token, db=db):
                raise TokenRevokedError()
            return token
        except TokenError:
            raise
        except Exception:
            raise RefreshTokenError()

    async def get_current_user(
        self,
        db: DBSession,
        uuid: UUID,
    ) -> User | None:
        """
        Retrieve the authenticated user by UUID.

        Args:
            db: The database session.
            uuid: The UUID of the user to retrieve.

        Returns:
            The User object if found, otherwise None.
        """
        return await UserService.get_by_uuid(db, uuid)

    async def get_current_active_session(
        self,
        db: DBSession,
        request: Request,
        user: User,
    ) -> UserSession:
        """
        Retrieve the currently active session for the request.

        Args:
            db: The database session.
            request: The incoming FastAPI request.
            user: The authenticated User object.

        Returns:
            The active UserSession object.

        Raises:
            AuthenticationError: If no active session is found for the user and request.
        """
        session = await SessionService.get_active_session_for_request(
            db=db,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        if not session:
            raise AuthenticationError(
                message=T("auth:session_expired_or_revoked"),
                code=401,
            )
        return session
