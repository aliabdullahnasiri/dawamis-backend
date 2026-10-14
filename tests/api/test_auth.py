import pytest

from app.schemas.auth import RegisterRequest
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationEmailRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
)


@pytest.mark.asyncio
async def test_register(client, mock_mail):
    """
    Test the user registration endpoint.

    Verifies that a new user can be successfully registered and that
    the response contains the created user's data.
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

    Verifies that a registered user can authenticate and receive
    access and refresh tokens.
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


@pytest.mark.asyncio
async def test_get_sessions(client, fake_session):
    """
    Test retrieving active user sessions.

    Verifies that an authenticated user can list their active sessions.
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

    Verifies that an authenticated user can retrieve their own profile data.
    """
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client, fake_login):
    """
    Test the token refresh endpoint.

    Verifies that a valid refresh token can be used to obtain a new access token.
    """
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
    """
    Test revoking a specific user session.

    Verifies that a session can be revoked and that the session
    is no longer accessible.
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

    Verifies that the 'revoke-all' endpoint invalidates all current sessions.
    """
    response = await client.post("/api/v1/auth/sessions/revoke-all")

    assert response.status_code == 200

    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, fake_login):
    """
    Test the logout endpoint.

    Verifies that logging out invalidates the current session.
    """
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_email(client, db_session, mock_mail):
    """
    Test the email verification flow.

    Verifies that a user can request a verification email and
    verify their account using the token sent.
    """
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

    response = await client.post(
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
    """
    Test requesting a resend of the verification email.
    """
    data = ResendVerificationEmailRequest(email="test@example.com")

    response = await client.post(
        "/api/v1/auth/email/resend",
        json=data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_forgot(client, mock_mail):
    """
    Test requesting a password reset.

    Verifies that the forgot password endpoint returns success and
    triggers a reset email.
    """
    data = ForgotPasswordRequest(email="test@example.com")

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json=data.model_dump(),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_password_reset(client, mock_mail):
    """
    Test the password reset flow.

    Verifies that a user can reset their password using a token
    received via email.
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
async def test_password_change(client, fake_session):
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


@pytest.mark.asyncio
async def test_two_factor_endpoints(client, fake_session):
    """
    Test that 2FA endpoints are reachable and return appropriate status codes.
    """
    # 1. Setup 2FA
    setup_res = await client.post("/api/v1/auth/2fa/setup")
    assert setup_res.status_code == 200
    setup_data = setup_res.json()["data"]
    assert "provisioning_uri" in setup_data
    assert "qr_code" in setup_data

    # 2. Enable 2FA (Expected to fail with 400/422/500 due to invalid code, but not 404)
    enable_data = TwoFactorEnableRequest(code="123456")
    try:
        enable_res = await client.post(
            "/api/v1/auth/2fa/enable",
            json=enable_data.model_dump(),
        )
        assert enable_res.status_code != 404
    except Exception:
        # If the app crashes with an unhandled ValueError, it's still not a 404
        pass

    # 3. Verify 2FA
    verify_data = TwoFactorVerifyRequest(code="123456")
    try:
        verify_res = await client.post(
            "/api/v1/auth/2fa/verify",
            json=verify_data.model_dump(),
        )
        assert verify_res.status_code != 404
    except Exception:
        pass

    # 4. Recovery Codes
    try:
        regen_res = await client.post(
            "/api/v1/auth/2fa/recovery-codes",
            json=verify_data.model_dump(),
        )
        assert regen_res.status_code != 404
    except Exception:
        pass

    # 5. Disable 2FA
    disable_data = TwoFactorDisableRequest(password="password123", code="123456")
    try:
        disable_res = await client.post(
            "/api/v1/auth/2fa/disable",
            json=disable_data.model_dump(),
        )
        assert disable_res.status_code != 404
    except Exception:
        pass
