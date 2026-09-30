from abc import ABC, abstractmethod
from typing import Any, Self

from celery import Task

from app.workers.meta import WorkerMeta


class BaseWorker(ABC, Task, metaclass=WorkerMeta):
    abstract = True

    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 5

    @abstractmethod
    def run(
        self: Self,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
