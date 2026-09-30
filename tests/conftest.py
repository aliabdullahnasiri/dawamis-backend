from collections.abc import AsyncGenerator
from unittest.mock import patch

import fakeredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import main as fastapi_app
from app.api.dependencies.db import get_db
from app.core.context.database import set_db
from app.models.base import Base
from app.schemas.auth.request import LoginRequest, RegisterRequest
from app.services.user_agent import UserAgentService

# --- Configuration ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    return engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables(db_engine):
    async with db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(
    db_engine,
) -> AsyncGenerator[AsyncSession, None]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        session = session_factory()

        set_db(session)

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
def app():
    return fastapi_app()


@pytest.fixture
def client(app, db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, base_url="http://127.0.0.1") as c:
        c.headers["User-Agent"] = UserAgentService().chrome()

        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_mail():
    with (
        patch("app.workers.email.EmailSendWorker.send") as mock_send,
        patch("app.workers.email.EmailSendWorker.send_template") as mock_template,
    ):
        yield {
            "send": mock_send,
            "send_template": mock_template,
        }


@pytest.fixture
def mock_redis(monkeypatch):
    fake_redis = fakeredis.FakeRedis(
        decode_responses=True,
    )

    import app.extensions.redis

    monkeypatch.setattr(
        app.extensions.redis,
        "redis",
        fake_redis,
    )

    return fake_redis


@pytest_asyncio.fixture
async def test_user(client: TestClient, mock_mail):
    # 1. Register a user
    reg_data = RegisterRequest(
        email="test@example.com",
        password="password123",
        user_name="sessionuser",
        accept_terms=True,
    )
    register_res = client.post("api/v1/auth/register", json=reg_data.model_dump())
    assert register_res.status_code == 201

    return register_res.json()["data"]


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    fake_useragent = UserAgentService().chrome()

    login_data = LoginRequest(
        email="test@example.com",
        password="password123",
    )

    login_res = client.post(
        "api/v1/auth/login",
        json=login_data.model_dump(),
        headers={"User-Agent": fake_useragent},
    )

    assert login_res.status_code == 200

    token = login_res.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}", "User-Agent": fake_useragent}
