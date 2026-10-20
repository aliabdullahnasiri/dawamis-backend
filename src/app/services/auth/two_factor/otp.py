import hashlib
import hmac
import secrets
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n.types import T
from app.core.encryption import SecretEncryption
from app.core.exceptions.authentication import InvalidTwoFactorCodeError
from app.enums.security import TwoFactorMethod
from app.models.user import User
from app.workers.email import EmailSendWorker

from .base import TwoFactorProvider


class OTPProvider(TwoFactorProvider):
    """
    Two-Factor Authentication provider using One-Time Passwords (OTP) sent via Email.
    Follows a secret-based architecture where codes are derived from a base secret.
    """

    def _derive_code(self, secret: str) -> str:
        """
        Derives a 6-digit OTP code from a base secret and the current time window.
        The window is 5 minutes to allow for email delivery delays.
        """
        # Use a 5-minute window for the time-based derivation
        window = str(int(time.time() // 300)).encode()

        # HMAC-SHA256(secret, window)
        digest = hmac.new(secret.encode(), window, hashlib.sha256).digest()

        # Convert bytes to integer and take last 6 digits
        code_int = int.from_bytes(digest, byteorder="big")
        return str(code_int % 10**6).zfill(6)

    async def setup(self, db: AsyncSession, user: User) -> dict[str, str]:
        """
        Initiates OTP setup by generating a base secret and sending a derived code.
        """
        # Generate a secure random base secret (similar to TOTP)
        base_secret = secrets.token_urlsafe(32)

        # Encrypt and store the base secret
        user.two_factor_secret_encrypted = None
        user.two_factor_pending_secret_encrypted = SecretEncryption.encrypt(base_secret)
        user.two_factor_method = TwoFactorMethod.OTP

        await db.commit()

        # Derive and send the code
        await self.send_code(user, base_secret)

        return {"message": "OTP sent to your email"}

    async def send_code(self, user: User, secret: str) -> str:
        """
        Derives the current OTP code from the base secret and sends it to the user's email.
        """
        code = self._derive_code(secret)

        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:otp_setup_subject"),
            text=T("emails:otp_setup_text"),
            template="emails/auth/otp_setup.html",
            otp_code=code,
            user=user.to_dict(),
        )

        return code

    async def verify(self, db: AsyncSession, user: User, code: str) -> bool:
        """
        Verifies the provided OTP code against the encrypted base secret.
        """
        if not user.two_factor_enabled or not user.two_factor_pending_secret_encrypted:
            return False

        # Decrypt the base secret and derive the current valid code
        base_secret = SecretEncryption.decrypt(user.two_factor_pending_secret_encrypted)
        return self._derive_code(base_secret) == code

    async def enable(self, db: AsyncSession, user: User, code: str) -> None:
        """
        Finalizes OTP enablement by verifying the code and promoting the secret.
        """
        if not user.two_factor_pending_secret_encrypted:
            return

        # Decrypt the pending base secret and derive the code
        base_secret = SecretEncryption.decrypt(user.two_factor_pending_secret_encrypted)

        if self._derive_code(base_secret) != code:
            raise InvalidTwoFactorCodeError()

        # Promote pending secret to active secret and enable 2FA
        user.two_factor_secret_encrypted = None
        user.two_factor_pending_secret_encrypted = None
        user.two_factor_enabled = True
