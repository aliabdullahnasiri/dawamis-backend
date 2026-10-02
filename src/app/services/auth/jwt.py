from datetime import timedelta
from typing import Any
from uuid import uuid4

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.revoked_token import RevokedToken
from app.services.datetime import DateTimeService


class JWTService:
    """Service responsible for JWT token operations."""

    @staticmethod
    def create_access_token(identity: Any, **claims: Any) -> str:
        """Create an access JWT for the given identity."""
        return JWTService._create_token(
            identity=identity,
            token_type="access",
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            claims=claims,
        )

    @staticmethod
    def create_refresh_token(identity: Any, **claims: Any) -> str:
        """Create a refresh JWT for the given identity."""
        return JWTService._create_token(
            identity=identity,
            token_type="refresh",
            expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            claims=claims,
        )

    @staticmethod
    def _create_token(
        identity: Any,
        token_type: str,
        expires_delta: timedelta,
        claims: dict[str, Any],
    ) -> str:
        """Create a JWT with standard and custom claims."""
        now = DateTimeService.utc_now()

        payload = {
            "sub": str(identity),
            "jti": str(uuid4()),
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
            **claims,
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def decode(token: str) -> dict[str, Any]:
        """Decode and validate a JWT."""
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

    @staticmethod
    def identity(token: str) -> Any:
        """Return the identity stored in the JWT."""
        claims = JWTService.decode(token)
        return claims["sub"]

    @staticmethod
    def claims(token: str) -> dict[str, Any]:
        """Return all claims from the JWT."""
        return JWTService.decode(token)

    @staticmethod
    async def revoke(token: str, db: AsyncSession) -> None:
        """Revoke a JWT."""
        claims = JWTService.decode(token)

        jti = claims["jti"]

        revoked_token = RevokedToken(jti=jti)

        db.add(revoked_token)
        await db.commit()

    @staticmethod
    async def is_revoked(token: str, db: AsyncSession) -> bool:
        """Check whether a JWT has been revoked."""
        claims = JWTService.decode(token)

        jti = claims["jti"]

        result = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        return result.scalar_one_or_none() is not None
