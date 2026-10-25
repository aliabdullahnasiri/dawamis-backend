from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_session import UserSession


@pytest.mark.asyncio
async def test_user_session_creation(db_session: AsyncSession):
    """
    Test basic UserSession model creation and relationship with User.
    """
    # Create a user first
    user = User(
        user_name="sessionuser",
        email="session@example.com",
    )
    user.set_password("password123")
    db_session.add(user)
    await db_session.commit()

    # Create a session for that user
    expires_at = datetime.now() + timedelta(days=1)
    session = UserSession(
        user_id=user.id,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0 (Test)",
        expires_at=expires_at,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.ip_address == "127.0.0.1"
    assert session.user_agent == "Mozilla/5.0 (Test)"
    assert session.expires_at == expires_at

from sqlalchemy import select
from sqlalchemy.orm import selectinload


@pytest.mark.asyncio
async def test_user_session_relationship(db_session: AsyncSession):
    """
    Test the back-population of sessions on the User model.
    """
    user = User(
        user_name="reluser",
        email="rel@example.com",
    )
    user.set_password("password123")
    db_session.add(user)
    await db_session.commit()

    # Create multiple sessions
    sessions = [
        UserSession(user_id=user.id, expires_at=datetime.now() + timedelta(days=1)),
        UserSession(user_id=user.id, expires_at=datetime.now() + timedelta(days=2)),
    ]
    db_session.add_all(sessions)
    await db_session.commit()

    # Eagerly load sessions to avoid MissingGreenlet
    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.sessions))
    )
    user = result.scalar_one()

    assert len(user.sessions) == 2
    assert all(s.user_id == user.id for s in user.sessions)
