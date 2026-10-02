from typing import Any, ClassVar, Self

from celery.schedules import crontab

from app.core.worker_database import get_worker_db
from app.services.session import SessionService
from app.workers.base import BaseWorker


class SessionCleanupWorker(BaseWorker):
    name = "session.cleanup"

    beat_schedule: ClassVar[dict[str, dict[str, Any]]] = {
        "cleanup-expired-sessions": {
            "task": "session.cleanup",
            "schedule": crontab(minute="*/15"),
        }
    }

    async def _run(self: Self) -> None:
        await self._cleanup()

    async def _cleanup(
        self: Self,
    ) -> None:
        async with get_worker_db() as db:
            await SessionService.cleanup(db=db)
