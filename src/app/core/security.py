from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.db import DBSession
from app.api.dependencies.oauth import OAuth2Token, RefreshToken
from app.services.jwt import JWTService


def get_current_token(
    db: DBSession,
    token: OAuth2Token,
) -> str:
    """
    Validate the access token and return it.

    The token is extracted from the Authorization header
    using the Bearer authentication scheme.

    Raises:
        HTTPException: If the token is invalid, expired,
            has an invalid type, or has been revoked.
    """
    try:
        claims = JWTService.decode(token)

        if claims.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if JWTService.is_revoked(token, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_claims(
    token: str = Depends(get_current_token),
) -> dict[str, Any]:
    """
    Return the claims from the currently authenticated access token.
    """
    return JWTService.claims(token)


def get_current_user_uuid(
    claims: dict[str, Any] = Depends(get_current_claims),
) -> str:
    """
    Return the authenticated user's UUID from the JWT subject claim.

    Raises:
        HTTPException: If the JWT does not contain a subject.
    """
    user_uuid = claims.get("sub")

    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_uuid


def get_current_refresh_token(
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
                detail="Invalid refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if JWTService.is_revoked(
            token=token,
            db=db,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
