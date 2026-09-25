import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.i18n.types import T
from app.models.user import User
from app.services.datetime import DateTimeService
from app.services.mail import MailService
from app.services.url import URLService
from app.services.user import UserService
from app.workers.email import EmailWorker


class PasswordResetService:
    """Service for handling password reset and recovery logic."""

    TOKEN_EXPIRE_MINUTES = 60

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    async def send_reset_email(
        cls: type[PasswordResetService],
        db: AsyncSession,
        email: str,
    ) -> None:
        """
        Generate a reset token and send it via email.
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

        await EmailWorker.send(
            MailService.send_template,
            to=user.email,
            subject=T("emails:password_reset_subject"),
            template="emails/auth/password_reset.html",
            user=user,
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
        Verify the token and reset the user's password.
        """
        token_hash = cls._hash_token(token)

        user: User = await UserService.get_by_reset_token(db=db, token_hash=token_hash)

        user.set_password(new_password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None

        await db.commit()

        await EmailWorker.send(
            MailService.send_template,
            to=user.email,
            subject=T("emails:password_reset_success_subject"),
            template="emails/auth/password_reset_success.html",
            user=user,
            app_url=settings.FRONTEND_URL,
        )
