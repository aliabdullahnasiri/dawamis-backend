from typing import ClassVar, Self

from celery.schedules import crontab

from app.workers.base import BaseWorker


class SessionCleanupWorker(BaseWorker):
    name = "session.cleanup"

    beat_schedule: ClassVar = {
        "cleanup-expired-sessions": {
            "task": "session.cleanup",
            "schedule": crontab(minute="*"),
        }
    }

    def run(self: Self) -> None: ...
