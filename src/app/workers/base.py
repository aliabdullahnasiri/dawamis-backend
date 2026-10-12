from abc import ABC, abstractmethod
from typing import Any, Self

from celery import Task

import app.core.worker_database as worker_db
from app.core.i18n.types import T
from app.workers.meta import WorkerMeta


class BaseWorker(ABC, Task, metaclass=WorkerMeta):
    """
    Abstract base class for all background workers in the application.

    Integrates Celery's Task with an asynchronous execution model via a
    custom event loop managed by worker_db.

    Attributes:
        abstract (bool): Marks the class as abstract to prevent instantiation.
        autoretry_for (tuple): Exceptions that trigger an automatic retry.
        retry_backoff (bool): Enables exponential backoff for retries.
        max_retries (int): Maximum number of retry attempts before failing.
    """
    abstract = True

    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 5

    def run(
        self: Self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Synchronous entry point for Celery. Orchestrates the execution of the
        asynchronous _run method using the worker's event loop.

        Args:
            *args: Positional arguments passed to the task.
            **kwargs: Keyword arguments passed to the task.

        Raises:
            RuntimeError: If the worker's event loop has not been initialized.
        """
        if worker_db.WorkerLoop is None:
            raise RuntimeError(T("worker:event_loop_not_initialized"))

        worker_db.WorkerLoop.run_until_complete(self._run(*args, **kwargs))

    @abstractmethod
    async def _run(self: Self, *args: Any, **kwargs: Any) -> None:
        """
        Asynchronous implementation of the worker's core logic.
        Must be implemented by all concrete worker subclasses.

        Args:
            *args: Positional arguments passed to the task.
            **kwargs: Keyword arguments passed to the task.
        """
        ...
