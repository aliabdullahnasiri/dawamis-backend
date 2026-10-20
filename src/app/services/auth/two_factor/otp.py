import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.authentication import InvalidTwoFactorCodeError
from app.models.user import User
from app.workers.email import EmailSendWorker

from .base import TwoFactorProvider


class OTPProvider(TwoFactorProvider):
    """
    Two-Factor Authentication provider using One-Time Passwords (OTP) sent via Email.
    """

    def _generate_otp_code(self) -> str:
        """
        Generates a random 6-digit OTP code.
        """
        return "".join([str(secrets.randbelow(10)) for _ in range(6)])

    async def setup(self, db: AsyncSession, user: User) -> dict[str, str]:
        """
        Initiates OTP setup by generating and sending a code.
        """
        code = self._generate_otp_code()

        # Store the OTP code temporarily (In a real app, this would go to Redis/DB)
        # For now, we use the pending_secret field as a temporary store
        user.two_factor_pending_secret_encrypted = code

        await EmailSendWorker.send_template(
            to=user.email,
            subject="Your Verification Code",
            text=f"Your verification code is {code}",
            template="emails/auth/otp_setup.html",
            code=code,
        )

        return {"message": "OTP sent to your email"}

    async def verify(self, db: AsyncSession, user: User, code: str) -> bool:
        """
        Verifies the provided OTP code.
        """
        if not user.two_factor_enabled or not user.two_factor_secret_encrypted:
            return False

        # In a real implementation, we'd check Redis for the latest code.
        # Here we check against the stored secret (if used as OTP secret).
        return user.two_factor_secret_encrypted == code

    async def enable(self, db: AsyncSession, user: User, code: str) -> None:
        """
        Finalizes OTP enablement.
        """
        if not user.two_factor_pending_secret_encrypted:
            return

        if user.two_factor_pending_secret_encrypted != code:
            raise InvalidTwoFactorCodeError()

        user.two_factor_enabled = True
        user.two_factor_pending_secret_encrypted = None
