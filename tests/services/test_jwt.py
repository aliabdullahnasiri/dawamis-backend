import pytest
import jwt
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth.jwt import JWTService
from app.core.config import settings

def test_create_access_token():
    identity = "user_123"
    extra_claim = {"role": "admin"}

    token = JWTService.create_access_token(identity, **extra_claim)

    assert isinstance(token, str)

    # Decode to verify contents
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == identity
    assert payload["type"] == "access"
    assert payload["role"] == "admin"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload

def test_create_refresh_token():
    identity = "user_456"

    token = JWTService.create_refresh_token(identity)

    assert isinstance(token, str)

    # Decode to verify contents
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == identity
    assert payload["type"] == "refresh"
    assert "jti" in payload

def test_decode_success():
    identity = "user_789"
    token = JWTService.create_access_token(identity)

    claims = JWTService.decode(token)

    assert claims["sub"] == identity
    assert claims["type"] == "access"

def test_decode_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        JWTService.decode("completely.invalid.token")

def test_decode_expired_token(monkeypatch):
    # Mock settings to have a very short expiry
    monkeypatch.setattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", -1)

    identity = "user_expired"
    token = JWTService.create_access_token(identity)

    with pytest.raises(jwt.ExpiredSignatureError):
        JWTService.decode(token)

def test_identity():
    identity = "user_identity"
    token = JWTService.create_access_token(identity)

    assert JWTService.identity(token) == identity

def test_claims():
    identity = "user_claims"
    extra = {"foo": "bar"}
    token = JWTService.create_access_token(identity, **extra)

    claims = JWTService.claims(token)
    assert claims["sub"] == identity
    assert claims["foo"] == "bar"

@pytest.mark.asyncio
async def test_revoke_and_is_revoked(db_session: AsyncSession):
    identity = "user_revoke"
    token = JWTService.create_access_token(identity)

    # Should not be revoked initially
    assert await JWTService.is_revoked(token, db_session) is False

    # Revoke it
    await JWTService.revoke(token, db_session)

    # Should now be revoked
    assert await JWTService.is_revoked(token, db_session) is True

@pytest.mark.asyncio
async def test_is_revoked_different_token(db_session: AsyncSession):
    token1 = JWTService.create_access_token("user1")
    token2 = JWTService.create_access_token("user2")

    await JWTService.revoke(token1, db_session)

    assert await JWTService.is_revoked(token1, db_session) is True
    assert await JWTService.is_revoked(token2, db_session) is False
