import base64
import hashlib
import io
import secrets
from datetime import UTC, datetime

import pyotp
import qrcode
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import SecretEncryption
from app.core.exceptions.authentication import (
    InvalidTwoFactorCodeError,
    InvalidTwoFactorPasswordError,
    TwoFactorAlreadyEnabledError,
    TwoFactorNotEnabledError,
    TwoFactorSetupRequiredError,
)
from app.models.recovery_code import RecoveryCode
from app.models.user import User


class TwoFactorService:
    """
    Service providing functionality for Two-Factor Authentication (2FA) using TOTP.

    This service handles the setup, enablement, verification, and management of
    Time-based One-Time Passwords (TOTP) and recovery codes for users.
    """

    @classmethod
    def _hash_recovery_code(cls: type[TwoFactorService], code: str) -> str:
        """
        Hashes a recovery code for secure storage.

        Args:
            code: The raw recovery code to hash.

        Returns:
            The SHA-256 hash of the normalized recovery code.
        """
        normalized = code.replace("-", "").strip().upper()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @classmethod
    def _generate_recovery_codes(cls: type[TwoFactorService]) -> list[str]:
        """
        Generates a set of random recovery codes.

        Returns:
            A list of generated recovery codes.
        """
        return [
            secrets.token_hex(5).upper() for _ in range(settings.RECOVERY_CODE_COUNT)
        ]

    @classmethod
    def _verify_totp(cls: type[TwoFactorService], secret: str, code: str) -> bool:
        """
        Verifies a TOTP code against a given secret.

        Args:
            secret: The TOTP secret.
            code: The 6-digit TOTP code to verify.

        Returns:
            True if the code is valid, False otherwise.
        """
        if len(code) != 6 or not code.isdigit():
            return False

        return pyotp.TOTP(secret).verify(
            code,
            valid_window=settings.TOTP_VALID_WINDOW,
        )


    @classmethod
    async def setup(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user: User,
    ) -> dict[str, str]:
        """
        Initiates the 2FA setup process for a user.

        Generates a TOTP secret and creates a QR code for the user to scan.

        Args:
            db: Database session.
            user: The user setting up 2FA.

        Returns:
            A dictionary containing the 'provisioning_uri' and 'qr_code' (base64).

        Raises:
            TwoFactorAlreadyEnabledError: If 2FA is already enabled for the user.
        """
        if user.totp_enabled:
            raise TwoFactorAlreadyEnabledError()

        secret = pyotp.random_base32()
        user.totp_pending_secret_encrypted = SecretEncryption.encrypt(secret)

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.APP_NAME,
        )

        image = qrcode.make(uri)
        buffer = io.BytesIO()
        image.save(buffer, "PNG")

        qr_code = base64.b64encode(buffer.getvalue()).decode()

        await db.commit()

        return {
            "provisioning_uri": uri,
            "qr_code": f"data:image/png;base64,{qr_code}",
        }

    @classmethod
    async def enable(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> list[str]:
        """
        Finalizes and enables 2FA for a user.

        Verifies the provided TOTP code and generates recovery codes.

        Args:
            db: Database session.
            user: The user enabling 2FA.
            code: The TOTP code for verification.

        Returns:
            A list of generated recovery codes.

        Raises:
            TwoFactorAlreadyEnabledError: If 2FA is already enabled.
            TwoFactorSetupRequiredError: If setup has not been initiated.
            InvalidTwoFactorCodeError: If the provided code is invalid.
        """
        if user.totp_enabled:
            raise TwoFactorAlreadyEnabledError()

        if not user.totp_pending_secret_encrypted:
            raise TwoFactorSetupRequiredError()

        secret = SecretEncryption.decrypt(user.totp_pending_secret_encrypted)

        if not cls._verify_totp(secret, code):
            raise InvalidTwoFactorCodeError()

        user.totp_secret_encrypted = user.totp_pending_secret_encrypted
        user.totp_pending_secret_encrypted = None
        user.totp_enabled = True

        codes = cls._generate_recovery_codes()

        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def verify_totp(
        cls: type[TwoFactorService],
        user: User,
        code: str,
    ) -> bool:
        """
        Verifies a TOTP code for a specific user.

        Args:
            user: The user whose code is being verified.
            code: The TOTP code to verify.

        Returns:
            True if the code is valid and 2FA is enabled, False otherwise.
        """
        if not user.totp_enabled or not user.totp_secret_encrypted:
            return False

        secret = SecretEncryption.decrypt(user.totp_secret_encrypted)

        return cls._verify_totp(secret, code)

    @classmethod
    async def verify_recovery_code(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> bool:
        """
        Verifies a recovery code for a user.

        If valid, marks the recovery code as used.

        Args:
            db: Database session.
            user: The user providing the recovery code.
            code: The recovery code to verify.

        Returns:
            True if the code is valid and unused, False otherwise.
        """
        if not user.totp_enabled:
            return False

        code_hash = cls._hash_recovery_code(code)

        result = await db.execute(
            select(RecoveryCode)
            .where(
                RecoveryCode.user_id == user.id,
                RecoveryCode.code_hash == code_hash,
                RecoveryCode.used_at.is_(None),
            )
            .with_for_update()
        )

        recovery_code = result.scalar_one_or_none()

        if recovery_code is None:
            return False

        recovery_code.used_at = datetime.now(UTC)
        await db.commit()

        return True

    @classmethod
    async def _replace_recovery_codes(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user_id: int,
        codes: list[str],
    ) -> None:
        """
        Replaces all existing recovery codes for a user with new ones.

        Args:
            db: Database session.
            user_id: The ID of the user.
            codes: The new recovery codes to store.
        """
        await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))

        for code in codes:
            db.add(
                RecoveryCode(
                    user_id=user_id,
                    code_hash=cls._hash_recovery_code(code),
                )
            )

    @classmethod
    async def regenerate_recovery_codes(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> list[str]:
        """
        Regenerates recovery codes for a user after TOTP verification.

        Args:
            db: Database session.
            user: The user requesting new codes.
            code: The TOTP code to verify the request.

        Returns:
            A list of newly generated recovery codes.

        Raises:
            TwoFactorNotEnabledError: If 2FA is not enabled for the user.
            InvalidTwoFactorCodeError: If the provided TOTP code is invalid.
        """
        if not user.totp_enabled:
            raise TwoFactorNotEnabledError()

        if not await cls.verify_totp(user, code):
            raise InvalidTwoFactorCodeError()

        codes = cls._generate_recovery_codes()

        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def disable(
        cls: type[TwoFactorService],
        db: AsyncSession,
        user: User,
        password: str,
        code: str,
    ) -> None:
        """
        Disables 2FA for a user after verifying password and TOTP code.

        Args:
            db: Database session.
            user: The user disabling 2FA.
            password: The user's password.
            code: The current TOTP code.

        Raises:
            InvalidTwoFactorPasswordError: If the password is incorrect.
            InvalidTwoFactorCodeError: If the TOTP code is invalid.
        """
        if not user.check_password(password):
            raise InvalidTwoFactorPasswordError()

        if not await cls.verify_totp(user, code):
            raise InvalidTwoFactorCodeError()

        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_pending_secret_encrypted = None

        await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
        await db.commit()
