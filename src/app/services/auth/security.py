from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.security import SecurityEventType
from app.models.security_event import SecurityEvent


class SecurityService:

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
        await cls.log_event(
            db,
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
