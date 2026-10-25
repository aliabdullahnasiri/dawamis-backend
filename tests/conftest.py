from typing import Any
from unittest.mock import patch

import fakeredis
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import main as fastapi_app
from app.core.context.database import set_db
from app.extensions.db import get_db
from app.models.base import Base
from app.schemas.auth.request import LoginRequest, RegisterRequest
from app.services.auth.user_agent import UserAgentService

# --- Configuration ---
# In-memory SQLite database for fast and isolated testing.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Creates a shared asynchronous SQLAlchemy engine for the entire test session.
    Uses a StaticPool to keep the in-memory database alive across multiple connections.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables(db_engine):
    """
    Initializes the database schema by creating all tables defined in the
    SQLAlchemy Base metadata.
    """
    async with db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(db_engine):
    """
    Provides a clean database session for each test.
    Wraps the session in a transaction that is rolled back at the end to ensure
    test isolation.
    """
    async with db_engine.connect() as connection:
        transaction = await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        async with session_factory() as session:
            set_db(session)

            try:
                yield session
            finally:
                await session.rollback()

        if transaction.is_active:
            await transaction.rollback()


@pytest.fixture
def app():
    """
    Returns the FastAPI application instance.
    """
    return fastapi_app()


@pytest_asyncio.fixture
async def client(app: FastAPI, db_session: AsyncSession, fake_useragent: str):
    """
    Provides an asynchronous HTTPX client for making requests to the API.
    Overrides the database dependency to use the test session.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={
                "User-Agent": fake_useragent,
            },
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_mail():
    """
    Mocks the EmailSendWorker to prevent actual emails from being sent during tests.
    """
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
    """
    Mocks the Redis client using fakeredis to avoid external dependencies.
    """
    fake_redis = fakeredis.FakeAsyncRedis(
        decode_responses=True,
    )

    from app import extensions

    monkeypatch.setattr(
        extensions,
        "redis",
        fake_redis,
    )

    return fake_redis


@pytest.fixture
def fake_useragent():
    """
    Generates a fake browser User-Agent for requests.
    """
    return UserAgentService().chrome()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient, fake_useragent: str, mock_mail):
    """
    Helper fixture that registers a test user and returns their data.
    """
    reg_data = RegisterRequest(
        email="anotheruser@example.com",
        password="password123",
        user_name="anotheruser",
        accept_terms=True,
    )

    response = await client.post(
        "/api/v1/auth/register",
        json=reg_data.model_dump(),
    )

    assert response.status_code == 201, response.text

    return response.json()["data"]


@pytest_asyncio.fixture
async def fake_session(client: AsyncClient, mock_mail) -> Any:
    """
    Helper fixture that registers a user and logs them in, returning the
    authenticated client headers.
    """
    # 1. Register a user
    reg_data = RegisterRequest(
        email="test@example.com",
        password="password123",
        user_name="sessionuser",
        accept_terms=True,
    )
    register_res = await client.post("api/v1/auth/register", json=reg_data.model_dump())
    assert register_res.status_code == 201

    # 2. Login the user
    login_data = LoginRequest(
        email="test@example.com",
        password="password123",
    )
    login_res = await client.post(
        "api/v1/auth/login",
        json=login_data.model_dump(),
    )
    assert login_res.status_code == 200

    token = login_res.json()["data"]["access_token"]

    client.headers.setdefault("Authorization", f"Bearer {token}")

    return client.headers


@pytest_asyncio.fixture
async def fake_login(client, test_user, mock_mail):
    """
    Helper fixture that logs in an existing test user and returns their auth data.
    """
    login_data = LoginRequest(
        email=test_user["email"],
        password="password123",
    )

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data.model_dump(),
    )

    assert response.status_code == 200, response.text

    token = response.json()["data"]["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"

    return response.json()["data"]
