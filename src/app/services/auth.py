from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n.types import T
from app.errors.exceptions import AuthenticationError
from app.models import User
from app.schemas.auth.request import RegisterRequest
from app.services.jwt import JWTService
from app.services.user import UserService
from app.workers.email import EmailSendWorker


class AuthService:
    """Authentication related business logic."""

    @staticmethod
    async def current_user(
        db: AsyncSession,
        user_uuid: UUID,
    ) -> User | None:
        """
        Return the currently authenticated user.
        """
        return await UserService.get_by_uuid(
            db=db,
            user_uuid=user_uuid,
        )

    @staticmethod
    async def register(
        db: AsyncSession,
        data: RegisterRequest,
    ) -> User:
        """
        Register a new user account.
        """
        return await UserService.create(
            db=db,
            data=data,
        )

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """
        Authenticate a user using email and password.

        Raises:
            AuthenticationError: If the credentials are invalid.
        """
        user = await UserService.get_by_email(
            db=db,
            email=email,
        )

        if user is None or not user.check_password(password):
            raise AuthenticationError(T("auth:invalid_credentials"))

        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        """
        Authenticate a user and create access and refresh tokens.
        """
        user = await AuthService.authenticate(
            db=db,
            email=email,
            password=password,
        )

        access_token = JWTService.create_access_token(
            identity=str(user.uuid),
        )

        refresh_token = JWTService.create_refresh_token(
            identity=str(user.uuid),
        )

        return access_token, refresh_token

    @staticmethod
    async def send_welcome_email(user: User) -> None:
        await EmailSendWorker.send_template(
            to=user.email,
            subject=T("emails:welcome_subject"),
            text=T("emails:welcome_text"),
            template="emails/auth/welcome.html",
            user=user.to_json(),
        )

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change the password for an authenticated user.
        """
        if not user.check_password(current_password):
            raise AuthenticationError(T("auth:invalid_current_password"))

        user.set_password(new_password)
        await db.commit()
