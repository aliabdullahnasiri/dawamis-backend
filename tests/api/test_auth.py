import pytest

from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationEmailRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)


@pytest.mark.asyncio
async def test_register(client, mock_mail):
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


@pytest.mark.asyncio
async def test_get_sessions(client, fake_session):
    response = await client.get("/api/v1/auth/sessions")

    assert response.status_code == 200

    sessions = response.json()["data"]
    assert isinstance(sessions, list)
    assert len(sessions) > 0


@pytest.mark.asyncio
async def test_me(client, fake_session):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client, fake_login):
    # This endpoint may require a refresh token in the Authorization header.
    # If so, use a test-specific dependency override instead of auth_headers.
    refresh_token = fake_login["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        headers={
            "Authorization": f"Bearer {refresh_token}",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.asyncio
async def test_revoke_session(client, fake_login):
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
    response = await client.post("/api/v1/auth/sessions/revoke-all")

    assert response.status_code == 200

    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, fake_login):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_email(client, db_session, mock_mail):
    data = RegisterRequest(
        email="verify@example.com",
        password="password123",
        user_name="verifyuser",
        accept_terms=True,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=data.model_dump(),
    )
    assert response.status_code == 201

    resend_data = ResendVerificationEmailRequest(email="verify@example.com")

    await client.post(
        "/api/v1/auth/email/resend",
        json=resend_data.model_dump(),
    )

    token = None

    for call in mock_mail["send_template"].call_args_list:
        _, kwargs = call
        if "token" in kwargs:
            token = kwargs["token"]
            break

    assert token is not None, "Verification token was not sent via email"

    verify_data = VerifyEmailRequest(token=token)

    response = await client.post(
        "/api/v1/auth/email/verify",
        json=verify_data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_email(client, mock_mail):
    data = ResendVerificationEmailRequest(email="test@example.com")

    response = await client.post(
        "/api/v1/auth/email/resend",
        json=data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_forgot(client, mock_mail):
    data = ForgotPasswordRequest(email="test@example.com")

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json=data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset(client, mock_mail):
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
async def test_password_change(client, fake_session):
    data = ChangePasswordRequest(
        current_password="password123",
        new_password="newpassword123",
    )

    response = await client.post(
        "/api/v1/auth/password/change",
        json=data.model_dump(),
    )

    assert response.status_code == 200
