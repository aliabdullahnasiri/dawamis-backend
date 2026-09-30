from abc import ABCMeta
from typing import Any

from app.core.celery import celery_app


class WorkerMeta(ABCMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(
            mcls,
            name,
            bases,
            namespace,
            **kwargs,
        )

        # Don't register the base worker itself
        if name != "BaseWorker":
            celery_app.register_task(cls())

        beat_schedule = namespace.get("beat_schedule")

        if beat_schedule:
            celery_app.conf.beat_schedule.update(beat_schedule)

        return cls
