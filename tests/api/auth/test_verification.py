import pytest
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
)

@pytest.mark.asyncio
async def test_verify_email(client, db_session, mock_mail):
    """
    Test the email verification flow.
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
