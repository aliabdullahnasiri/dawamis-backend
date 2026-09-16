from celery import Task

from app.workers.meta import WorkerMeta


class BaseWorker(Task, metaclass=WorkerMeta):
    abstract = True

    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 5
