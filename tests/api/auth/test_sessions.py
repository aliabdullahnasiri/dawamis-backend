import pytest
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    LoginRequest,
)

@pytest.mark.asyncio
async def test_register(client, mock_mail):
    """
    Test the user registration endpoint.
    """
    data = RegisterRequest(
        email="newuser@example.com",
        password="password123",
        user_name="newuser",
        accept_terms=True,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=data.model_dump(),
    )

    assert response.status_code == 201
    assert "data" in response.json()
    assert response.json()["data"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_login(client, mock_mail):
    """
    Test the user login endpoint.
    """
    data = RegisterRequest(
        email="loginuser@example.com",
        password="password123",
        user_name="loginuser",
        accept_terms=True,
    )

    register_response = await client.post(
        "/api/v1/auth/register",
        json=data.model_dump(),
    )
    assert register_response.status_code == 201

    login_data = LoginRequest(
        email="loginuser@example.com",
        password="password123",
    )

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data.model_dump(),
    )

    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert "refresh_token" in response.json()["data"]

    return response.json()["data"]
