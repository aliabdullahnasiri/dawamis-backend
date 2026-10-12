import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from celery.signals import worker_process_init
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.i18n.types import T

# The event loop used by the worker process to run asynchronous tasks.
WorkerLoop: asyncio.AbstractEventLoop | None = None

# The asynchronous SQLAlchemy engine for the worker process.
WorkerEngine: AsyncEngine | None = None

# The session factory for creating asynchronous database sessions in the worker.
WorkerLocalSession: async_sessionmaker[AsyncSession] | None = None


@worker_process_init.connect
def init_worker_database(**kwargs: object) -> None:
    """
    Initializes the database connection and event loop for the Celery worker process.

    This function is connected to the 'worker_process_init' signal, ensuring that
    each worker child process has its own isolated event loop and database engine,
    avoiding issues with sharing async resources across process boundaries.
    """
    global WorkerLoop
    global WorkerEngine
    global WorkerLocalSession

    WorkerLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(WorkerLoop)

    WorkerEngine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
    )

    WorkerLocalSession = async_sessionmaker(
        bind=WorkerEngine,
        autoflush=False,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_worker_db() -> AsyncIterator[AsyncSession]:
    """
    Async context manager that provides a database session for the worker.

    Yields:
        An AsyncSession instance for database operations.

    Raises:
        RuntimeError: If the worker database session factory has not been initialized.
    """
    if WorkerLocalSession is None:
        raise RuntimeError(T("worker:database_not_initialized"))

    async with WorkerLocalSession() as session:
        yield session
