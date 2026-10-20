from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.i18n.types import T
from app.models import User
from app.schemas.auth import RegisterRequest
from app.services.auth.jwt import JWTService
from app.services.user import UserService
from app.workers.email import EmailSendWorker


class AuthService:
    """
    Service handling the primary authentication business logic.

    This service provides methods for user registration, authentication,
    login, password management, and account-related notifications.
    """


    @staticmethod
    async def current_user(
        db: AsyncSession,
        user_uuid: UUID,
    ) -> User | None:
        """
        Retrieve the currently authenticated user by their UUID.

        Args:
            db: Database session.
            user_uuid: The unique identifier of the user.

        Returns:
            The User object if found, otherwise None.
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
        Register a new user account in the system.

        Args:
            db: Database session.
            data: The registration data containing email, password, etc.

        Returns:
            The newly created User object.
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
        Authenticate a user using their email and password.

        Args:
            db: Database session.
            email: The user's email address.
            password: The plain-text password to verify.

        Returns:
            The authenticated User object.

        Raises:
            AuthenticationError: If the user is not found or the password is invalid.
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
        Authenticate a user and generate session tokens.

        This method verifies credentials and returns a pair of access and refresh tokens.

        Args:
            db: Database session.
            email: The user's email address.
            password: The user's password.

        Returns:
            A tuple containing (access_token, refresh_token).

        Raises:
            AuthenticationError: If authentication fails.
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
        """
        Send a welcome email to a newly registered user.

        Args:
            user: The user to receive the welcome email.
        """
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

        Verifies the current password before updating to the new one.

        Args:
            db: Database session.
            user: The user requesting the password change.
            current_password: The user's existing password for verification.
            new_password: The new password to set.

        Raises:
            AuthenticationError: If the current password is incorrect.
        """
        if not user.check_password(current_password):
            raise AuthenticationError(T("auth:invalid_current_password"))


        user.set_password(new_password)
        await db.commit()
