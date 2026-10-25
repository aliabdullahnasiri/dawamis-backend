from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decorators import handle_exception
from app.core.exceptions import (
    EmailVerificationTokenExpiredError,
    PasswordResetTokenExpiredError,
    UserNotFound,
)
from app.core.exceptions.authentication import InvalidPasswordResetTokenError
from app.core.i18n.types import T
from app.models import User
from app.schemas.user.request.profile import CreateUserRequest, UpdateUserRequest
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
    async def update(
        db: AsyncSession,
        user: User,
        data: UpdateUserRequest,
    ) -> User:
        """
        Update user profile information.
        """
        update_data = data.model_dump(exclude_unset=True)

        # Uniqueness checks for username and email
        if "user_name" in update_data and update_data["user_name"] != user.user_name:
            existing_user = await UserService.get_by_username(db, update_data["user_name"])
            if existing_user:
                raise UserNotFound(message=T("user_name:user_name_already_exists"))

        if "email" in update_data and update_data["email"] != user.email:
            existing_user = await UserService.get_by_email(db, update_data["email"])
            if existing_user:
                raise UserNotFound(message=T("email:email_already_exists"))

        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_email(
        db: AsyncSession,
        user: User,
        new_email: str,
    ) -> User:
        """
        Update user email with uniqueness check.
        """
        # Check if the email is already taken by another user
        existing_user = (
            await db.execute(select(User).where(User.email == new_email))
        ).scalar_one_or_none()

        if existing_user and existing_user.uuid != user.uuid:
            raise UserNotFound(message=T("email:email_already_exists"))

        user.email = new_email
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_username(
        db: AsyncSession,
        user: User,
        new_username: str,
    ) -> User:
        """
        Update user username with uniqueness check.
        """
        # Check if the username is already taken by another user
        existing_user = (
            await db.execute(select(User).where(User.user_name == new_username))
        ).scalar_one_or_none()

        if existing_user and existing_user.uuid != user.uuid:
            raise UserNotFound(message=T("user_name:user_name_already_exists"))

        user.user_name = new_username
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
            raise EmailVerificationTokenExpiredError()

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
            raise InvalidPasswordResetTokenError()

        if (
            user.password_reset_expires_at is None
            or user.password_reset_expires_at < DateTimeService.utc_now()
        ):
            raise PasswordResetTokenExpiredError()

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
