from abc import ABC, abstractmethod
from typing import Any, Self

from celery import Task

import app.core.worker_database as worker_db
from app.core.i18n.types import T
from app.workers.meta import WorkerMeta


class BaseWorker(ABC, Task, metaclass=WorkerMeta):
    abstract = True

    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 5

    def run(
        self: Self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if worker_db.WorkerLoop is None:
            raise RuntimeError(T("worker:event_loop_not_initialized"))

        worker_db.WorkerLoop.run_until_complete(self._run(*args, **kwargs))

    @abstractmethod
    async def _run(self: Self) -> None: ...
