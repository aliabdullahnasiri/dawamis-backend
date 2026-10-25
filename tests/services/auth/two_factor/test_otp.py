import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.auth.two_factor.otp import OTPProvider
from app.enums.security import TwoFactorMethod
from app.core.exceptions.authentication import (
    InvalidTwoFactorCodeError,
    TwoFactorSetupRequiredError,
)

@pytest.fixture
def otp_provider():
    return OTPProvider()

@pytest.fixture
def mock_user():
    return User(
        user_name="testuser",
        email="test@example.com",
        two_factor_enabled=False,
    )

@pytest.mark.asyncio
async def test_otp_derive_code(otp_provider):
    """
    Test that the OTP code is correctly derived and is 6 digits.
    """
    secret = "test_secret_12345"
    code = otp_provider._derive_code(secret)

    assert len(code) == 6
    assert code.isdigit()

    # Verify stability within the same 5-minute window
    code2 = otp_provider._derive_code(secret)
    assert code == code2

@pytest.mark.asyncio
async def test_otp_setup(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test the OTP setup process.
    """
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock) as mock_send:
        result = await otp_provider.setup(db_session, mock_user)

        assert result == {"message": "OTP sent to your email"}
        assert mock_user.two_factor_method == TwoFactorMethod.OTP
        assert mock_user.two_factor_pending_secret_encrypted is not None
        assert mock_user.two_factor_enabled is False

        # Verify email was sent
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert kwargs["to"] == mock_user.email
        assert "otp_code" in kwargs

@pytest.mark.asyncio
async def test_otp_verify_success(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test successful verification of an OTP code.
    """
    # Setup the user with a pending secret
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock):
        await otp_provider.setup(db_session, mock_user)

    from app.core.encryption import SecretEncryption

    # Get the pending secret and decrypt it
    pending_secret_encrypted = mock_user.two_factor_pending_secret_encrypted
    base_secret = SecretEncryption.decrypt(pending_secret_encrypted)
    valid_code = otp_provider._derive_code(base_secret)

    # For verify to return True, the user must have two_factor_enabled=True or we must mock it
    # because the current implementation of verify is:
    # if not user.two_factor_enabled or not user.two_factor_pending_secret_encrypted:
    #     return False
    mock_user.two_factor_enabled = True

    is_valid = await otp_provider.verify(db_session, mock_user, valid_code)
    assert is_valid is True

@pytest.mark.asyncio
async def test_otp_verify_failure(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test verification failure with wrong code.
    """
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock):
        await otp_provider.setup(db_session, mock_user)

    is_valid = await otp_provider.verify(db_session, mock_user, "000000")
    assert is_valid is False

@pytest.mark.asyncio
async def test_otp_enable_success(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test successful enablement of OTP.
    """
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock):
        await otp_provider.setup(db_session, mock_user)

    from app.core.encryption import SecretEncryption
    base_secret = SecretEncryption.decrypt(mock_user.two_factor_pending_secret_encrypted)
    valid_code = otp_provider._derive_code(base_secret)

    await otp_provider.enable(db_session, mock_user, valid_code)

    assert mock_user.two_factor_enabled is True
    assert mock_user.two_factor_pending_secret_encrypted is None

@pytest.mark.asyncio
async def test_otp_enable_failure(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test enablement failure with wrong code.
    """
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock):
        await otp_provider.setup(db_session, mock_user)

    with pytest.raises(InvalidTwoFactorCodeError):
        await otp_provider.enable(db_session, mock_user, "000000")

@pytest.mark.asyncio
async def test_otp_resend_success(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test resending an OTP code.
    """
    with patch("app.workers.email.EmailSendWorker.send_template", new_callable=AsyncMock) as mock_send:
        await otp_provider.setup(db_session, mock_user)

        await otp_provider.resend(db_session, mock_user)

        # Should have been called twice (once for setup, once for resend)
        assert mock_send.call_count == 2

@pytest.mark.asyncio
async def test_otp_resend_failure(otp_provider, db_session: AsyncSession, mock_user):
    """
    Test resending when no setup is pending.
    """
    with pytest.raises(TwoFactorSetupRequiredError):
        await otp_provider.resend(db_session, mock_user)
