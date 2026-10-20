import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions.authentication import (
    InvalidTwoFactorCodeError,
    InvalidTwoFactorPasswordError,
    TwoFactorAlreadyEnabledError,
    TwoFactorNotEnabledError,
)
from app.models.recovery_code import RecoveryCode
from app.models.user import User

from .base import TwoFactorProvider
from .otp import OTPProvider
from .totp import TOTPProvider


class TwoFactorService:
    """
    Orchestrator service for Two-Factor Authentication (2FA).
    Delegates method-specific logic to specialized providers.
    """

    # Provider registry
    _providers: dict[str, TwoFactorProvider] = {
        "totp": TOTPProvider(),
        "otp": OTPProvider(),
    }

    @classmethod
    def _get_provider(cls, method: str) -> TwoFactorProvider:
        provider = cls._providers.get(method.lower())
        if not provider:
            raise ValueError(f"Unsupported 2FA method: {method}")
        return provider

    @classmethod
    def _hash_recovery_code(cls, code: str) -> str:
        normalized = code.replace("-", "").strip().upper()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @classmethod
    def _generate_recovery_codes(cls) -> list[str]:
        return [
            secrets.token_hex(5).upper() for _ in range(settings.RECOVERY_CODE_COUNT)
        ]

    @classmethod
    async def setup(
        cls,
        db: AsyncSession,
        user: User,
        method: str = "totp",
    ) -> dict[str, Any]:
        """
        Initiates the 2FA setup process using the specified method.
        """
        if user.two_factor_enabled:
            raise TwoFactorAlreadyEnabledError()

        provider = cls._get_provider(method)
        return await provider.setup(db, user)

    @classmethod
    async def enable(
        cls,
        db: AsyncSession,
        user: User,
        code: str,
        method: str = "totp",
    ) -> list[str]:
        """
        Finalizes and enables 2FA for a user.
        """
        if user.two_factor_enabled:
            raise TwoFactorAlreadyEnabledError()

        provider = cls._get_provider(method)

        try:
            await provider.enable(db, user, code)
        except ValueError:
            raise InvalidTwoFactorCodeError()

        # Common logic: generate recovery codes
        codes = cls._generate_recovery_codes()
        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def verify(
        cls,
        db: AsyncSession,
        user: User,
        code: str,
    ) -> bool:
        """
        Verifies a 2FA code based on the user's enabled method.
        """
        if not user.two_factor_enabled:
            return False

        # Note: User model should have two_factor_method field.
        # Fallback to 'totp' if not yet set during migration.
        method = getattr(user, "two_factor_method", "totp") or "totp"
        provider = cls._get_provider(method)

        return await provider.verify(db, user, code)

    @classmethod
    async def verify_recovery_code(
        cls,
        db: AsyncSession,
        user: User,
        code: str,
    ) -> bool:
        """
        Verifies a recovery code for a user.
        """
        if not user.two_factor_enabled:
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
        cls,
        db: AsyncSession,
        user_id: int,
        codes: list[str],
    ) -> None:
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
        cls,
        db: AsyncSession,
        user: User,
        code: str,
    ) -> list[str]:
        """
        Regenerates recovery codes after 2FA verification.
        """
        if not user.two_factor_enabled:
            raise TwoFactorNotEnabledError()

        if not await cls.verify(db, user, code):
            raise InvalidTwoFactorCodeError()

        codes = cls._generate_recovery_codes()
        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def disable(
        cls,
        db: AsyncSession,
        user: User,
        password: str,
        code: str,
    ) -> None:
        """
        Disables 2FA for a user after verifying password and code.
        """
        if not user.check_password(password):
            raise InvalidTwoFactorPasswordError()

        if not await cls.verify(db, user, code):
            raise InvalidTwoFactorCodeError()

        user.two_factor_enabled = False
        user.two_factor_secret_encrypted = None
        user.two_factor_pending_secret_encrypted = None

        await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
        await db.commit()
