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

WorkerLoop: asyncio.AbstractEventLoop | None = None

WorkerEngine: AsyncEngine | None = None

WorkerLocalSession: async_sessionmaker[AsyncSession] | None = None


@worker_process_init.connect
def init_worker_database(**kwargs: object) -> None:
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
    if WorkerLocalSession is None:
        raise RuntimeError(T("worker:database_not_initialized"))

    async with WorkerLocalSession() as session:
        yield session
