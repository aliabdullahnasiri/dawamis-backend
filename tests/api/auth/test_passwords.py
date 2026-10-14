import pytest
from httpx import AsyncClient
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

@pytest.mark.asyncio
async def test_password_forgot(client: AsyncClient, mock_mail):
    """
    Test requesting a password reset.
    """
    data = ForgotPasswordRequest(email="test@example.com")

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json=data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset(client: AsyncClient, mock_mail):
    """
    Test the password reset flow.
    """
    data = RegisterRequest(
        email="reset@example.com",
        password="password123",
        user_name="resetuser",
        accept_terms=True,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=data.model_dump(),
    )

    assert response.status_code == 201

    reset_request = ForgotPasswordRequest(email="reset@example.com")

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json=reset_request.model_dump(),
    )

    assert response.status_code == 200

    token = None

    for call in mock_mail["send_template"].call_args_list:
        _, kwargs = call
        if "token" in kwargs:
            token = kwargs["token"]
            break

    assert token is not None, "Password reset token was not sent via email"

    reset_data = ResetPasswordRequest(
        token=token,
        new_password="newpassword123",
    )

    response = await client.post(
        "/api/v1/auth/password/reset",
        json=reset_data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_change(client: AsyncClient, fake_session):
    """
    Test changing the password while authenticated.
    """
    data = ChangePasswordRequest(
        current_password="password123",
        new_password="newpassword123",
    )

    response = await client.post(
        "/api/v1/auth/password/change",
        json=data.model_dump(),
    )

    assert response.status_code == 200
