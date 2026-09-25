import pytest

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.auth.request import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResendVerificationEmailRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)


@pytest.mark.asyncio
async def test_register(client):
    data = RegisterRequest(
        email="newuser@example.com",
        password="password123",
        user_name="newuser",
        accept_terms=True,
    )
    response = client.post("api/v1/auth/register", json=data.model_dump())
    assert response.status_code == 201
    assert "data" in response.json()
    assert response.json()["data"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_login(client):
    # First register a user
    data = RegisterRequest(
        email="loginuser@example.com",
        password="password123",
        user_name="loginuser",
        accept_terms=True,
    )
    client.post("api/v1/auth/register", json=data.model_dump())

    # Now login
    login_data = LoginRequest(
        email="loginuser@example.com",
        password="password123",
    )
    response = client.post("api/v1/auth/login", json=login_data.model_dump())
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    assert "refresh_token" in response.json()["data"]


@pytest.mark.asyncio
async def test_me(client, auth_headers):
    response = client.get("api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    response = client.post("api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200

    # Token should now be revoked
    response = client.get("api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, test_user):
    from app.services.jwt import JWTService

    refresh_token = JWTService.create_refresh_token(identity=str(test_user.uuid))
    headers = {"Authorization": f"Bearer {refresh_token}"}

    response = client.post("api/v1/auth/refresh", headers=headers)
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.asyncio
async def test_verify_email(client, db_session, mock_mail):
    # Create a user that isn't verified
    data = RegisterRequest(
        email="verify@example.com",
        password="password123",
        user_name="verifyuser",
        accept_terms=True,
    )
    client.post("api/v1/auth/register", json=data.model_dump())

    # 1. Request verification email to generate token
    resend_data = ResendVerificationEmailRequest(email="verify@example.com")
    client.post("api/v1/auth/email/resend", json=resend_data.model_dump())

    # 2. Extract token from the mocked mail call
    # The EmailWorker calls MailService.send_template.
    # We find the call where 'token' was passed.
    token = None
    for call in mock_mail["send_template"].call_args_list:
        args, kwargs = call
        if "token" in kwargs:
            token = kwargs["token"]
            break

    assert token is not None, "Verification token was not sent via email"

    # 3. Verify the email using the intercepted token
    verify_data = VerifyEmailRequest(token=token)
    response = client.post("api/v1/auth/email/verify", json=verify_data.model_dump())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_email(client, mock_mail):
    data = ResendVerificationEmailRequest(email="test@example.com")
    response = client.post("api/v1/auth/email/resend", json=data.model_dump())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_forgot(client, mock_mail):
    data = ForgotPasswordRequest(email="test@example.com")
    response = client.post("api/v1/auth/password/forgot", json=data.model_dump())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset(client, mock_mail):
    # 1. Create a user
    data = RegisterRequest(
        email="reset@example.com",
        password="password123",
        user_name="resetuser",
        accept_terms=True,
    )

    response = client.post(
        "/api/v1/auth/register",
        json=data.model_dump(),
    )

    assert response.status_code == 201

    # 2. Request password reset email
    reset_data = ForgotPasswordRequest(
        email="reset@example.com",
    )

    response = client.post(
        "/api/v1/auth/password/forgot",
        json=reset_data.model_dump(),
    )

    assert response.status_code == 200

    # 3. Extract reset token from mocked email
    token = None

    for call in mock_mail["send_template"].call_args_list:
        _, kwargs = call

        if "token" in kwargs:
            token = kwargs["token"]
            break

    assert token is not None, "Password reset token was not sent via email"

    # 4. Reset the password using the token
    reset_confirm_data = ResetPasswordRequest(
        token=token,
        new_password="newpassword123",
    )

    response = client.post(
        "/api/v1/auth/password/reset",
        json=reset_confirm_data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_change(client, auth_headers):
    data = ChangePasswordRequest(
        current_password="password123", new_password="newpassword123"
    )
    response = client.post(
        "api/v1/auth/password/change", json=data.model_dump(), headers=auth_headers
    )
    assert response.status_code == 200
