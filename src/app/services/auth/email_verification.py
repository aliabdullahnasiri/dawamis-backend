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


class EmailVerificationService:

    TOKEN_EXPIRE_MINUTES = 30

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    async def send(
        cls: type[EmailVerificationService],
        db: AsyncSession,
        user: User,
    ) -> None:
        token = cls._generate_token()
        token_hash = cls._hash_token(token)

        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = DateTimeService.utc_now() + timedelta(
            minutes=cls.TOKEN_EXPIRE_MINUTES
        )

        await db.commit()

        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:verify_email_subject"),
            template="emails/auth/verify_email.html",
            user=user.to_json(),
            token=token,
            verification_url=URLService.email_verification(token=token),
        )

    @classmethod
    async def verify(
        cls: type[EmailVerificationService],
        db: AsyncSession,
        token: str,
    ) -> None:
        token_hash = cls._hash_token(token)

        user: User = await UserService.get_by_verification_token(
            db=db, token=token_hash
        )

        user.is_email_verified = True
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None

        await db.commit()

        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:email_verified_success_subject"),
            template="emails/auth/email_verified.html",
            user=user.to_json(),
            app_url=settings.FRONTEND_URL,
        )
