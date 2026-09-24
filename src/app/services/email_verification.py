import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.api.dependencies.db import DBSession
from app.core.i18n.types import T
from app.models.user import User
from app.services.mail import MailService
from app.services.url import URLService
from app.services.user import UserService
from app.workers.email import EmailWorker


class EmailVerificationService:

    TOKEN_EXPIRE_MINUTES = 30

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def send(
        cls: type[EmailVerificationService],
        db: DBSession,
        user: User,
    ) -> None:
        token = cls._generate_token()
        token_hash = cls._hash_token(token)

        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = datetime.now(UTC) + timedelta(
            minutes=cls.TOKEN_EXPIRE_MINUTES
        )

        db.commit()

        EmailWorker.send(
            MailService.send_template,
            to=user.email,
            subject=T("emails:verify_email_subject"),
            template="emails/auth/verify_email.html",
            user=user,
            token=token,
            verification_url=URLService.email_verification(token=token),
        )

    @classmethod
    def verify(
        cls: type[EmailVerificationService],
        db: DBSession,
        token: str,
    ) -> None:
        token_hash = cls._hash_token(token)

        user: User = UserService.get_by_verification_token(db=db, token=token_hash)

        user.is_email_verified = True
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None

        db.commit()
