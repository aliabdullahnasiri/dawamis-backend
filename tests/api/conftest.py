from datetime import timedelta

import pytest_asyncio

from app.models import User, UserSession
from app.services.auth.jwt import JWTService
from app.services.datetime import DateTimeService


@pytest_asyncio.fixture
async def identity(client, db_session):
    user = User(
        user_name="org-owner", email="owner@example.com", password_hash="unused"
    )
    db_session.add(user)
    await db_session.flush()
    session = UserSession(
        user=user,
        ip_address="127.0.0.1",
        user_agent=client.headers["user-agent"],
        expires_at=DateTimeService.utc_now() + timedelta(days=1),
    )
    db_session.add(session)
    await db_session.commit()
    client.headers["Authorization"] = (
        f"Bearer {JWTService.create_access_token(user.uuid)}"
    )
    return user, session
