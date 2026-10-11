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
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
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
    async with db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(db_engine):
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
    return fastapi_app()


@pytest_asyncio.fixture
async def client(app: FastAPI, db_session: AsyncSession, fake_useragent: str):
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
    fake_redis = fakeredis.FakeAsyncRedis(
        decode_responses=True,
    )

    import app.extensions as extensions

    monkeypatch.setattr(
        extensions,
        "redis",
        fake_redis,
    )

    return fake_redis


@pytest.fixture
def fake_useragent():
    return UserAgentService().chrome()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient, fake_useragent: str, mock_mail):
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
