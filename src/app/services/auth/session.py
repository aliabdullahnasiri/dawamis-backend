from datetime import timedelta
from typing import Any, Type
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SessionNotFoundError
from app.models.user_session import UserSession
from app.services.datetime import DateTimeService


class SessionService:
    """
    Service responsible for managing user sessions.

    Handles session creation, retrieval, revocation, and periodic cleanup.
    """

    @classmethod
    async def get_or_create_session(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_in_seconds: int = 86400 * 30,
    ) -> UserSession:
        """
        Retrieve an existing active session for the given device or create a new one.

        Args:
            db: The database session.
            user_id: UUID of the user.
            ip_address: IP address of the request.
            user_agent: User agent of the request.
            expires_in_seconds: Session expiration time in seconds.

        Returns:
            The active UserSession object.
        """
        now = DateTimeService.utc_now()

        # Search for an existing active session from the same device
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.ip_address == ip_address,
                UserSession.user_agent == user_agent,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            # Reuse existing session: update last used timestamp
            session.last_used_at = now
            await db.commit()
            await db.refresh(session)
            return session

        # No existing session found: create a new one
        return await cls.create_session(
            db=db,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_in_seconds=expires_in_seconds,
        )

    @classmethod
    async def get_active_session_for_request(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession | None:
        """
        Retrieve an active session that matches the current request's identity and device.

        Args:
            db: The database session.
            user_id: UUID of the user.
            ip_address: IP address of the request.
            user_agent: User agent of the request.

        Returns:
            The matching UserSession object if found, otherwise None.
        """
        now = DateTimeService.utc_now()

        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.ip_address == ip_address,
                UserSession.user_agent == user_agent,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def create_session(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_in_seconds: int = 86400 * 30,
    ) -> UserSession:
        """
        Create a new user session.

        Args:
            db: The database session.
            user_id: UUID of the user.
            ip_address: IP address of the request.
            user_agent: User agent of the request.
            expires_in_seconds: Session expiration time in seconds.

        Returns:
            The created UserSession object.
        """
        now = DateTimeService.utc_now()

        session = UserSession(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            last_used_at=now,
            expires_at=now + timedelta(seconds=expires_in_seconds),
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    @classmethod
    async def get_user_sessions(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
    ) -> list[UserSession]:
        """
        Retrieve all active sessions for a specific user.

        Args:
            db: The database session.
            user_id: UUID of the user.

        Returns:
            A list of active UserSession objects, ordered by last used date.
        """
        now = DateTimeService.utc_now()

        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .order_by(UserSession.last_used_at.desc())
        )

        result = await db.execute(stmt)

        return list(result.scalars().all())

    @classmethod
    async def get_user_session(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        session_uuid: UUID,
    ) -> UserSession:
        """
        Retrieve a specific user session by its UUID.

        Args:
            db: The database session.
            user_id: UUID of the user.
            session_uuid: UUID of the session to retrieve.

        Returns:
            The UserSession object.

        Raises:
            SessionNotFoundError: If the session is not found for the given user.
        """
        stmt = select(UserSession).where(
            UserSession.uuid == session_uuid,
            UserSession.user_id == user_id,
        )

        result = await db.execute(stmt)

        session = result.scalar_one_or_none()

        if session is None:
            raise SessionNotFoundError()

        return session

    @classmethod
    async def revoke_session(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        session_uuid: UUID,
    ) -> None:
        """
        Revoke a specific user session.

        Args:
            db: The database session.
            user_id: UUID of the user.
            session_uuid: UUID of the session to revoke.
        """
        session = await cls.get_user_session(
            db=db,
            user_id=user_id,
            session_uuid=session_uuid,
        )

        if session.revoked_at is None:
            session.revoked_at = DateTimeService.utc_now()

            await db.commit()

    @classmethod
    async def revoke_all_sessions(
        cls: Type[SessionService],
        db: AsyncSession,
        user_id: int,
        exclude_session_id: int | None = None,
    ) -> None:
        """
        Revoke all active sessions for a specific user.

        Args:
            db: The database session.
            user_id: UUID of the user.
            exclude_session_id: Optional ID of a session to keep active.
        """
        now = DateTimeService.utc_now()

        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
            )
        )

        if exclude_session_id is not None:
            stmt = stmt.where(
                UserSession.id != exclude_session_id,
            )

        await db.execute(stmt)
        await db.commit()

    @classmethod
    async def cleanup(cls: Type[SessionService], *, db: AsyncSession) -> None:
        """
        Clean up expired sessions from the database.

        This method is typically called by a background worker.
        """
        now = DateTimeService.utc_now()
        cutoff = now - timedelta(days=30)

        await db.execute(delete(UserSession).where(UserSession.expires_at < cutoff))

        await db.commit()
