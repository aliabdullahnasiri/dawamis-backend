from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import CreateUserRequest


class UserService:
    """
    Provides business logic for user management.

    This service handles user creation, retrieval, updating,
    deletion, authentication, and password management.
    """

    @staticmethod
    def create(
        db: Session,
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
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_by_uuid(
        db: Session,
        user_uuid: UUID,
    ) -> User | None:
        """
        Return a user by UUID.
        """
        return db.execute(
            select(User).where(User.uuid == user_uuid)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_username(
        db: Session,
        user_name: str,
    ) -> User | None:
        """
        Return a user by username.
        """
        return db.execute(
            select(User).where(User.user_name == user_name)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_email(
        db: Session,
        email: str,
    ) -> User | None:
        """
        Return a user by email.
        """
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    @staticmethod
    def get_all(
        db: Session,
    ) -> list[User]:
        """
        Return all users.
        """
        return list(db.execute(select(User)).scalars().all())

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
    def delete(
        db: Session,
        user: User,
    ) -> None:
        """
        Delete a user.
        """
        db.delete(user)
        db.commit()
