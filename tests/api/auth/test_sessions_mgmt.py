import pytest
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    LoginRequest,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
)
from app.schemas.auth.response import (
    LogoutResponse,
    RefreshResponse,
    RevokeSessionResponse,
    SessionsResponse,
)
from app.schemas.user.data import UserData
from app.services.auth import AuthService
from app.services.auth.jwt import JWTService
from app.services.auth.rate_limit import AuthRateLimiter
from app.services.auth.security import SecurityService
from app.services.auth.session import SessionService
from app.services.user import UserService

# Re-implementing the session-specific tests from old test_auth.py
# to ensure they are complete.

@pytest.mark.asyncio
async def test_get_sessions(client, fake_session):
    """
    Test retrieving active user sessions.
    """
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    sessions = response.json()["data"]
    assert isinstance(sessions, list)
    assert len(sessions) > 0

@pytest.mark.asyncio
async def test_me(client, fake_session):
    """
    Test the 'get current user' endpoint.
    """
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_refresh_token(client, fake_login):
    """
    Test the token refresh endpoint.
    """
    refresh_token = fake_login["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

@pytest.mark.asyncio
async def test_revoke_session(client, fake_login):
    """
    Test revoking a specific user session.
    """
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    sessions = response.json()["data"]
    assert len(sessions) > 0
    session_uuid = sessions[0]["uuid"]
    response = await client.delete(f"/api/v1/auth/sessions/{session_uuid}")
    assert response.status_code == 200
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_revoke_all_sessions(client, fake_login):
    """
    Test revoking all active user sessions.
    """
    response = await client.post("/api/v1/auth/sessions/revoke-all")
    assert response.status_code == 200
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_logout(client, fake_login):
    """
    Test the logout endpoint.
    """
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
