from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n.types import T
from app.errors.exceptions import AppError
from app.models.user_session import UserSession
from app.services.datetime import DateTimeService


class SessionService:
    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> list[UserSession]:
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

    async def get_user_session(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: UUID,
    ) -> UserSession:
        stmt = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )

        result = await db.execute(stmt)

        session = result.scalar_one_or_none()

        if session is None:
            raise AppError(
                message=T("auth:session_not_found"),
                status_code=404,
            )

        return session

    async def revoke_session(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: UUID,
    ) -> None:
        session = await self.get_user_session(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )

        if session.revoked_at is None:
            session.revoked_at = DateTimeService.utc_now()

            await db.commit()

    async def revoke_all_sessions(
        self,
        db: AsyncSession,
        user_id: UUID,
        exclude_session_id: UUID | None = None,
    ) -> None:
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
