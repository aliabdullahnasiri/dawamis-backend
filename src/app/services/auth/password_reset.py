import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.i18n.types import T
from app.models.user import User
from app.services.datetime import DateTimeService
from app.services.url import URLService
from app.services.user import UserService
from app.workers.email import EmailSendWorker


class PasswordResetService:
    """
    Service for handling password reset and recovery logic.

    This service handles generating reset tokens, sending reset emails,
    and performing the actual password update.
    """


    TOKEN_EXPIRE_MINUTES = 60

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash a reset token for secure storage.

        Args:
            token: The raw token string.

        Returns:
            The SHA-256 hash of the token.
        """
        return hashlib.sha256(token.encode()).hexdigest()


    @staticmethod
    def _generate_token() -> str:
        """
        Generate a secure random reset token.

        Returns:
            A URL-safe random token string.
        """
        return secrets.token_urlsafe(32)


    @classmethod
    async def send_reset_email(
        cls: type[PasswordResetService],
        db: AsyncSession,
        email: str,
    ) -> None:
        """
        Generate a reset token and send a password reset email.

        If the user is not found, the method returns silently to prevent email enumeration.

        Args:
            db: Database session.
            email: The email address requesting the reset.
        """
        try:

            user: User = await UserService.get_by_email(db=db, email=email)
        except Exception:
            # Generic failure for security to prevent email enumeration
            return

        token = cls._generate_token()
        token_hash = cls._hash_token(token)

        user.password_reset_token_hash = token_hash
        user.password_reset_expires_at = DateTimeService.utc_now() + timedelta(
            minutes=cls.TOKEN_EXPIRE_MINUTES
        )

        await db.commit()

        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:password_reset_subject"),
            template="emails/auth/password_reset.html",
            user=user.to_json(),
            token=token,
            reset_url=URLService.password_reset(token=token),
        )

    @classmethod
    async def reset_password(
        cls: type[PasswordResetService],
        db: AsyncSession,
        token: str,
        new_password: str,
    ) -> None:
        """
        Verify the reset token and update the user's password.

        Args:
            db: Database session.
            token: The reset token provided by the user.
            new_password: The new password to set.
        """
        token_hash = cls._hash_token(token)


        user: User = await UserService.get_by_reset_token(db=db, token_hash=token_hash)

        user.set_password(new_password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None

        await db.commit()

        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:password_reset_success_subject"),
            template="emails/auth/password_reset_success.html",
            user=user.to_json(),
            app_url=settings.FRONTEND_URL,
        )
