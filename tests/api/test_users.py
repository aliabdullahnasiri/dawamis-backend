import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.schemas.auth.request import LoginRequest, RegisterRequest


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """
    Fixture to provide an authenticated client.
    """
    # Register user
    reg_data = RegisterRequest(
        email="testuser@example.com",
        password="password123",
        user_name="testuser",
        accept_terms=True,
    )
    await client.post("/api/v1/auth/register", json=reg_data.model_dump())

    # Login user
    login_data = LoginRequest(
        email="testuser@example.com",
        password="password123",
    )
    response = await client.post("/api/v1/auth/login", json=login_data.model_dump())
    token = response.json()["data"]["access_token"]

    # Create a new client with authorization header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.mark.asyncio
async def test_get_me(auth_client):
    """
    Test the GET /users/me endpoint.
    """
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_name"] == "testuser"
    assert data["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_update_me(auth_client):
    """
    Test the PATCH /users/me endpoint.
    """
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
    }
    response = await auth_client.patch("/api/v1/users/me", json=update_data)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"


@pytest.mark.asyncio
async def test_update_my_email(auth_client):
    """
    Test the PATCH /users/me/email endpoint.
    """
    update_data = {
        "email": "updated_email@example.com",
    }
    response = await auth_client.patch("/api/v1/users/me/email", json=update_data)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "updated_email@example.com"


@pytest.mark.asyncio
async def test_update_my_username(auth_client):
    """
    Test the PATCH /users/me/username endpoint.
    """
    update_data = {
        "user_name": "updated_username",
    }
    response = await auth_client.patch("/api/v1/users/me/username", json=update_data)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_name"] == "updated_username"


@pytest.mark.asyncio
async def test_delete_me(auth_client):
    """
    Test the DELETE /users/me endpoint.
    """
    response = await auth_client.delete("/api/v1/users/me")
    assert response.status_code == 204

    # Verify the user is gone by trying to access /me
    # Since get_current_user now returns None if the user is missing,
    # and get_current_active_session raises AuthenticationError (401) when user is None,
    # the expected status code is 401 Unauthorized.
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 401
