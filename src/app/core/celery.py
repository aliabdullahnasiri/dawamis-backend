from celery import Celery

from app.core.config import settings

# The Celery application instance used for background task processing.
celery_app = Celery(
    settings.APP_NAME,
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=False,
)

# IMPORTANT: Initialize worker database connections and event loop for Celery worker processes.
__import__("app.core.worker_database")  # noqa: F401
