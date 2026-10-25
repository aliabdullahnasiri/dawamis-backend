import pytest
from httpx import AsyncClient

# Re-implementing the session-specific tests from old test_auth.py
# to ensure they are complete.

@pytest.mark.asyncio
async def test_get_sessions(client: AsyncClient, fake_session):
    """
    Test retrieving active user sessions.
    """
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    sessions = response.json()["data"]
    assert isinstance(sessions, list)
    assert len(sessions) > 0

@pytest.mark.asyncio
async def test_me(client: AsyncClient, fake_session):
    """
    Test the 'get current user' endpoint.
    """
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, fake_login):
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
async def test_revoke_session(client: AsyncClient, fake_login):
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
async def test_revoke_all_sessions(client: AsyncClient, fake_login):
    """
    Test revoking all active user sessions.
    """
    response = await client.post("/api/v1/auth/sessions/revoke-all")
    assert response.status_code == 200
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_logout(client: AsyncClient, fake_login):
    """
    Test the logout endpoint.
    """
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
