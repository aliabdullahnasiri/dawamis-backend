import base64
import hashlib
import io
import secrets
from datetime import UTC, datetime
from typing import Type

import pyotp
import qrcode
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import SecretEncryption
from app.core.i18n.types import T
from app.models.recovery_code import RecoveryCode
from app.models.user import User


class TwoFactorService:
    @classmethod
    def _hash_recovery_code(cls: Type[TwoFactorService], code: str) -> str:
        normalized = code.replace("-", "").strip().upper()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @classmethod
    def _generate_recovery_codes(cls: Type[TwoFactorService]) -> list[str]:
        return [
            secrets.token_hex(5).upper() for _ in range(settings.RECOVERY_CODE_COUNT)
        ]

    @classmethod
    def _verify_totp(cls: Type[TwoFactorService], secret: str, code: str) -> bool:
        if len(code) != 6 or not code.isdigit():
            return False

        return pyotp.TOTP(secret).verify(
            code,
            valid_window=1,
        )

    @classmethod
    async def setup(
        cls: Type[TwoFactorService],
        db: AsyncSession,
        user: User,
    ) -> dict[str, str]:
        if user.totp_enabled:
            raise ValueError(T("auth:two_factor_already_enabled"))

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
        cls: Type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> list[str]:
        if user.totp_enabled:
            raise ValueError(T("auth:two_factor_already_enabled"))

        if not user.totp_pending_secret_encrypted:
            raise ValueError(T("auth:two_factor_setup_required"))

        secret = SecretEncryption.decrypt(user.totp_pending_secret_encrypted)

        if not cls._verify_totp(secret, code):
            raise ValueError(T("auth:invalid_two_factor_code"))

        user.totp_secret_encrypted = user.totp_pending_secret_encrypted
        user.totp_pending_secret_encrypted = None
        user.totp_enabled = True

        codes = cls._generate_recovery_codes()

        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def verify_totp(
        cls: Type[TwoFactorService],
        user: User,
        code: str,
    ) -> bool:
        if not user.totp_enabled or not user.totp_secret_encrypted:
            return False

        secret = SecretEncryption.decrypt(user.totp_secret_encrypted)

        return cls._verify_totp(secret, code)

    @classmethod
    async def _replace_recovery_codes(
        cls: Type[TwoFactorService],
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
        cls: Type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> list[str]:
        if not user.totp_enabled:
            raise ValueError(T("auth:two_factor_not_enabled"))

        if not await cls.verify_totp(user, code):
            raise ValueError(T("auth:invalid_two_factor_code"))

        codes = cls._generate_recovery_codes()

        await cls._replace_recovery_codes(db, user.id, codes)
        await db.commit()

        return codes

    @classmethod
    async def verify_recovery_code(
        cls: Type[TwoFactorService],
        db: AsyncSession,
        user: User,
        code: str,
    ) -> bool:
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
