from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.security import SecurityEventType
from app.models.security_event import SecurityEvent


class SecurityService:
    """
    Service for logging security-related events.

    Provides methods to track login successes, failures, suspicious activities,
    and account lockouts for auditing and security monitoring.
    """

    @classmethod
    async def log_event(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        event_type: SecurityEventType,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """
        Log a general security event to the database.

        Args:
            db: Database session.
            event_type: The type of security event.
            user_id: Optional user ID associated with the event.
            ip_address: Optional IP address of the event source.
            user_agent: Optional user agent of the event source.
            metadata: Optional additional metadata about the event.

        Returns:
            The created SecurityEvent object.
        """
        event = SecurityEvent(

            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata,
        )

        db.add(event)
        await db.commit()

        return event

    @classmethod
    async def login_success(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Log a successful login event.

        Args:
            db: Database session.
            user_id: The ID of the user who logged in.
            ip_address: Optional IP address of the request.
            user_agent: Optional user agent of the request.
        """
        await cls.log_event(

            db,
            event_type=SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def login_failed(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Log a failed login attempt.

        Args:
            db: Database session.
            user_id: Optional ID of the user who attempted to login.
            ip_address: Optional IP address of the request.
            user_agent: Optional user agent of the request.
        """
        await cls.log_event(

            db,
            event_type=SecurityEventType.LOGIN_FAILED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    async def suspicious_login(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        reason: str,
    ) -> None:
        """
        Log a suspicious login event.

        Args:
            db: Database session.
            user_id: The ID of the user.
            ip_address: Optional IP address of the request.
            user_agent: Optional user agent of the request.
            reason: The reason why the login was flagged as suspicious.
        """
        await cls.log_event(

            db,
            event_type=SecurityEventType.SUSPICIOUS_LOGIN,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "reason": reason,
            },
        )

    @classmethod
    async def account_locked(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        attempts: int,
    ) -> None:
        """
        Log an account lockout event.

        Args:
            db: Database session.
            user_id: The ID of the locked user.
            ip_address: Optional IP address of the request.
            user_agent: Optional user agent of the request.
            attempts: The number of failed attempts that led to the lockout.
        """
        await cls.log_event(

            db,
            event_type=SecurityEventType.ACCOUNT_LOCKED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "failed_attempts": attempts,
            },
        )

    @classmethod
    async def rate_limit_exceeded(
        cls: type[SecurityService],
        db: AsyncSession,
        *,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Log a rate limit exceeded event.

        Args:
            db: Database session.
            user_id: Optional ID of the user.
            ip_address: Optional IP address of the request.
            user_agent: Optional user agent of the request.
        """
        await cls.log_event(

            db,
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
