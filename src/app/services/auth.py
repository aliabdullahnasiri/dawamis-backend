from uuid import UUID

from sqlalchemy.orm import Session

from app.core.i18n.types import T
from app.errors.exceptions import AuthenticationError
from app.models import User
from app.schemas.auth.request import RegisterRequest
from app.services.jwt import JWTService
from app.services.user import UserService


class AuthService:
    """Authentication related business logic."""

    @staticmethod
    def current_user(
        db: Session,
        user_uuid: UUID,
    ) -> User | None:
        """
        Return the currently authenticated user.
        """
        return UserService.get_by_uuid(
            db=db,
            user_uuid=user_uuid,
        )

    @staticmethod
    def register(
        db: Session,
        data: RegisterRequest,
    ) -> User:
        """
        Register a new user account.
        """
        return UserService.create(
            db=db,
            data=data,
        )

    @staticmethod
    def authenticate(
        db: Session,
        email: str,
        password: str,
    ) -> User:
        """
        Authenticate a user using email and password.

        Raises:
            AuthenticationError: If the credentials are invalid.
        """
        user = UserService.get_by_email(
            db=db,
            email=email,
        )

        if user is None or not user.check_password(password):
            raise AuthenticationError(T("auth:invalid_credentials"))

        return user

    @staticmethod
    def login(
        db: Session,
        email: str,
        password: str,
    ) -> tuple[str, str]:
        """
        Authenticate a user and create access and refresh tokens.
        """
        user = AuthService.authenticate(
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
