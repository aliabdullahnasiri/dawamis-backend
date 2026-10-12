from abc import ABCMeta
from typing import Any

from app.core.celery import celery_app


class WorkerMeta(ABCMeta):
    """
    Metaclass for BaseWorker and its subclasses.

    Handles automatic registration of workers with the Celery application
    and configures scheduled tasks (beat schedules) defined in the worker class.
    """

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        """
        Creates a new worker class and registers it if it is not the BaseWorker.

        Args:
            mcls: The metaclass.
            name: Name of the class being created.
            bases: Base classes of the new class.
            namespace: Class attributes and methods.
            **kwargs: Additional arguments.

        Returns:
            The newly created worker class.
        """
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
