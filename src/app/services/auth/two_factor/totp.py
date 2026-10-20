import base64
import io
import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.encryption import SecretEncryption
from app.models.user import User
from .base import TwoFactorProvider

class TOTPProvider(TwoFactorProvider):
    """
    Two-Factor Authentication provider using Time-based One-Time Passwords (TOTP).
    """

    def _verify_totp(self, secret: str, code: str) -> bool:
        """
        Verifies a TOTP code against a given secret.
        """
        if len(code) != 6 or not code.isdigit():
            return False

        return pyotp.TOTP(secret).verify(
            code,
            valid_window=settings.TOTP_VALID_WINDOW,
        )

    async def setup(self, db: AsyncSession, user: User) -> dict[str, str]:
        """
        Generates a TOTP secret and creates a QR code.
        """
        secret = pyotp.random_base32()
        user.two_factor_pending_secret_encrypted = SecretEncryption.encrypt(secret)

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.APP_NAME,
        )

        image = qrcode.make(uri)
        buffer = io.BytesIO()
        image.save(buffer, "PNG")

        qr_code = base64.b64encode(buffer.getvalue()).decode()

        return {
            "provisioning_uri": uri,
            "qr_code": f"data:image/png;base64,{qr_code}",
        }

    async def verify(self, db: AsyncSession, user: User, code: str) -> bool:
        """
        Verifies a TOTP code for a user.
        """
        if not user.two_factor_secret_encrypted:
            return False

        secret = SecretEncryption.decrypt(user.two_factor_secret_encrypted)
        return self._verify_totp(secret, code)

    async def enable(self, db: AsyncSession, user: User, code: str) -> None:
        """
        Finalizes TOTP enablement.
        """
        if not user.two_factor_pending_secret_encrypted:
            from app.core.exceptions.authentication import TwoFactorSetupRequiredError
            raise TwoFactorSetupRequiredError()

        secret = SecretEncryption.decrypt(user.two_factor_pending_secret_encrypted)

        if not self._verify_totp(secret, code):
            raise ValueError("Invalid TOTP code")

        user.two_factor_secret_encrypted = user.two_factor_pending_secret_encrypted
        user.two_factor_pending_secret_encrypted = None
        user.two_factor_enabled = True
