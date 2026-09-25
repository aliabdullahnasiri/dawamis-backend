from typing import Generator
from unittest.mock import patch

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app import main as fastapi_app
from app.api.dependencies.db import get_db
from app.models.base import Base

# --- Configuration ---
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(db_engine) -> Generator:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)(autoflush=False, autocommit=False)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def app():
    return fastapi_app()


@pytest.fixture
def client(app, db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_mail():
    with (
        patch("app.services.mail.MailService.send") as mock_send,
        patch("app.services.mail.MailService.send_template") as mock_template,
    ):
        yield {"send": mock_send, "send_template": mock_template}


@pytest.fixture
def mock_redis(monkeypatch):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    # The object we want to replace is the 'redis' instance defined in 'app.extensions.redis'.
    # Because we are importing it as 'from app.extensions import redis' in some places
    # and using 'app.extensions.redis.redis' in monkeypatch, it's failing.
    # Let's use a more robust way to patch the module level object.
    import app.extensions.redis

    app.extensions.redis.redis = fake_redis
    return fake_redis


@pytest.fixture
def test_user(db_session):
    from app.models.user import User

    user = User(
        email="test@example.com",
        user_name="testuser",
        is_email_verified=True,
    )
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client, test_user):
    from app.services.jwt import JWTService

    access_token = JWTService.create_access_token(identity=str(test_user.uuid))
    return {"Authorization": f"Bearer {access_token}"}
