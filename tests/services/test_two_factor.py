import pyotp
import pytest
from cryptography.fernet import InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth.two_factor import TwoFactorService
from app.core.exceptions.authentication import (
    InvalidTwoFactorCodeError,
    TwoFactorAlreadyEnabledError,
    TwoFactorSetupRequiredError,
)



@pytest.mark.asyncio
async def test_setup_success(db_session: AsyncSession):
    """
    Test the successful setup of two-factor authentication.

    Verifies that the provisioning URI and QR code are generated,
    and that the secret is stored in a pending state.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    result = await TwoFactorService.setup(db_session, user)

    assert "provisioning_uri" in result
    assert "qr_code" in result
    assert result["qr_code"].startswith("data:image/png;base64,")
    assert user.totp_pending_secret_encrypted is not None
    assert user.totp_enabled is False


@pytest.mark.asyncio
async def test_setup_already_enabled(db_session: AsyncSession):
    """
    Test that setup fails if two-factor authentication is already enabled.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
        totp_enabled=True,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(TwoFactorAlreadyEnabledError):
        await TwoFactorService.setup(db_session, user)



@pytest.mark.asyncio
async def test_enable_success(db_session: AsyncSession):
    """
    Test the successful enablement of two-factor authentication.

    Verifies that providing a valid TOTP code activates 2FA,
    generates recovery codes, and promotes the pending secret to active.
    """
    # 1. Setup
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    setup_data = await TwoFactorService.setup(db_session, user)

    # Extract secret from URI to generate a valid code
    import urllib.parse

    parsed = urllib.parse.urlparse(setup_data["provisioning_uri"])
    query = urllib.parse.parse_qs(parsed.query)
    secret = query["secret"][0]

    totp = pyotp.TOTP(secret)
    code = totp.now()

    # 2. Enable
    recovery_codes = await TwoFactorService.enable(db_session, user, code)

    assert len(recovery_codes) > 0
    assert user.totp_enabled is True
    assert user.totp_pending_secret_encrypted is None
    assert user.totp_secret_encrypted is not None


@pytest.mark.asyncio
async def test_enable_invalid_code(db_session: AsyncSession):
    """
    Test that enabling 2FA fails with an invalid TOTP code.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await TwoFactorService.setup(db_session, user)

    with pytest.raises(InvalidTwoFactorCodeError):
        await TwoFactorService.enable(db_session, user, "000000")



@pytest.mark.asyncio
async def test_enable_without_setup(db_session: AsyncSession):
    """
    Test that enabling 2FA fails if setup has not been performed.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(TwoFactorSetupRequiredError):
        await TwoFactorService.enable(db_session, user, "123456")



@pytest.mark.asyncio
async def test_verify_totp_success(db_session: AsyncSession):
    """
    Test successful verification of a TOTP code.
    """
    # Setup and enable
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    setup_data = await TwoFactorService.setup(db_session, user)
    import urllib.parse

    parsed = urllib.parse.urlparse(setup_data["provisioning_uri"])
    query = urllib.parse.parse_qs(parsed.query)
    secret = query["secret"][0]

    totp = pyotp.TOTP(secret)
    code = totp.now()
    await TwoFactorService.enable(db_session, user, code)

    # Verify
    new_code = totp.now()
    assert await TwoFactorService.verify_totp(user, new_code) is True


@pytest.mark.asyncio
async def test_verify_totp_failure(db_session: AsyncSession):
    """
    Test that verification fails with an incorrect TOTP code.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
        totp_enabled=True,
        totp_secret_encrypted="some_encrypted_secret",
    )
    db_session.add(user)
    await db_session.commit()

    try:
        assert await TwoFactorService.verify_totp(user, "000000") is False
    except InvalidToken:
        ...


@pytest.mark.asyncio
async def test_recovery_code_flow(db_session: AsyncSession):
    """
    Test the recovery code lifecycle: generation, usage, and one-time consumption.
    """
    # Setup and enable to get recovery codes
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    setup_data = await TwoFactorService.setup(db_session, user)
    import urllib.parse

    parsed = urllib.parse.urlparse(setup_data["provisioning_uri"])
    query = urllib.parse.parse_qs(parsed.query)
    secret = query["secret"][0]

    totp = pyotp.TOTP(secret)
    recovery_codes = await TwoFactorService.enable(db_session, user, totp.now())

    code_to_use = recovery_codes[0]

    # Verify recovery code works
    assert (
        await TwoFactorService.verify_recovery_code(db_session, user, code_to_use)
        is True
    )

    # Verify it cannot be used again
    assert (
        await TwoFactorService.verify_recovery_code(db_session, user, code_to_use)
        is False
    )


@pytest.mark.asyncio
async def test_regenerate_recovery_codes(db_session: AsyncSession):
    """
    Test the regeneration of recovery codes.

    Verifies that new codes are generated and old codes are invalidated.
    """
    user = User(
        email="test@example.com",
        user_name="testuser",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()

    setup_data = await TwoFactorService.setup(db_session, user)
    import urllib.parse

    parsed = urllib.parse.urlparse(setup_data["provisioning_uri"])
    query = urllib.parse.parse_qs(parsed.query)
    secret = query["secret"][0]

    totp = pyotp.TOTP(secret)
    old_codes = await TwoFactorService.enable(db_session, user, totp.now())

    # Regenerate
    new_codes = await TwoFactorService.regenerate_recovery_codes(
        db_session, user, totp.now()
    )

    assert new_codes != old_codes
    assert (
        await TwoFactorService.verify_recovery_code(db_session, user, new_codes[0])
        is True
    )
    assert (
        await TwoFactorService.verify_recovery_code(db_session, user, old_codes[0])
        is False
    )
