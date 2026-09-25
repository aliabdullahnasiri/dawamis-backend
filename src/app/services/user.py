from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decorators import handle_exception
from app.core.i18n.types import T
from app.errors.exceptions import AppError, UserNotFound
from app.models import User
from app.schemas.user import CreateUserRequest
from app.services.datetime import DateTimeService


class UserService:
    """
    Provides business logic for user management.

    This service handles user creation, retrieval, updating,
    deletion, authentication, and password management.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        data: CreateUserRequest,
    ) -> User:
        """
        Create a new user.
        """
        user = User(
            first_name=data.first_name,
            middle_name=data.middle_name,
            last_name=data.last_name,
            user_name=data.user_name,
            email=data.email,
            birthday=data.birthday,
        )

        user.set_password(data.password)

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    @handle_exception(NoResultFound, _raise=UserNotFound)
    async def get_by_uuid(
        db: AsyncSession,
        user_uuid: UUID,
    ) -> User:
        """
        Return a user by UUID.
        """
        return (
            await db.execute(select(User).where(User.uuid == user_uuid))
        ).scalar_one()

    @staticmethod
    @handle_exception(NoResultFound, _raise=UserNotFound)
    async def get_by_username(
        db: AsyncSession,
        user_name: str,
    ) -> User:
        """
        Return a user by username.
        """
        return (
            await db.execute(select(User).where(User.user_name == user_name))
        ).scalar_one()

    @staticmethod
    @handle_exception(NoResultFound, _raise=UserNotFound)
    async def get_by_email(
        db: AsyncSession,
        email: str,
    ) -> User:
        """
        Return a user by email.
        """
        return (await db.execute(select(User).where(User.email == email))).scalar_one()

    @staticmethod
    async def get_by_verification_token(db: AsyncSession, token: str) -> User:
        user: User | None = (
            await db.execute(
                select(User).where(User.email_verification_token_hash == token)
            )
        ).scalar_one_or_none()

        if user is None:
            raise UserNotFound(message=T("errors:invalid_email_verification_token"))

        if (
            user.email_verification_expires_at is None
            or user.email_verification_expires_at < DateTimeService.utc_now()
        ):
            raise AppError(
                message=T("errors:email_verification_token_expired"),
                status_code=400,
                code="email_verification_token_expired",
            )

        return user

    @staticmethod
    async def get_by_reset_token(db: AsyncSession, token_hash: str) -> User:
        """
        Return a user by their password reset token hash.
        """
        user: User | None = (
            await db.execute(
                select(User).where(User.password_reset_token_hash == token_hash)
            )
        ).scalar_one_or_none()

        if user is None:
            raise UserNotFound(message=T("errors:invalid_password_reset_token"))

        if (
            user.password_reset_expires_at is None
            or user.password_reset_expires_at < DateTimeService.utc_now()
        ):
            raise AppError(
                message=T("errors:password_reset_token_expired"),
                status_code=400,
                code="password_reset_token_expired",
            )

        return user

    @staticmethod
    async def get_all(
        db: AsyncSession,
    ) -> list[User]:
        """
        Return all users.
        """
        return list((await db.execute(select(User))).scalars().all())

    @staticmethod
    def verify_password(
        user: User,
        password: str,
    ) -> bool:
        """
        Verify a user's password.
        """
        return user.check_password(password)

    @staticmethod
    async def delete(
        db: AsyncSession,
        user: User,
    ) -> None:
        """
        Delete a user.
        """
        await db.delete(user)
        await db.commit()
