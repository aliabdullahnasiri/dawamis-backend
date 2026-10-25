import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.enums.security import SecurityEventType

@pytest.mark.asyncio
async def test_security_event_creation(db_session: AsyncSession):
    """
    Test basic SecurityEvent model creation.
    """
    user = User(
        user_name="testuser", 
        email="test@example.com", 
        password_hash="dummy_hash"
    )
    db_session.add(user)
    await db_session.commit()

    event = SecurityEvent(
        user_id=user.id,
        event_type=SecurityEventType.LOGIN_SUCCESS,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        metadata_={"browser": "Chrome", "os": "Linux"},
    )
    db_session.add(event)
    await db_session.commit()

    assert event.id is not None
    assert event.event_type == SecurityEventType.LOGIN_SUCCESS
    assert event.ip_address == "127.0.0.1"
    assert event.metadata_ == {"browser": "Chrome", "os": "Linux"}

@pytest.mark.asyncio
async def test_security_event_anonymous(db_session: AsyncSession):
    """
    Test SecurityEvent creation without a user (anonymous event).
    """
    event = SecurityEvent(
        event_type=SecurityEventType.LOGIN_FAILED,
        ip_address="192.168.1.1",
        metadata_={"attempted_username": "admin"},
    )
    db_session.add(event)
    await db_session.commit()

    assert event.id is not None
    assert event.user_id is None
    assert event.event_type == SecurityEventType.LOGIN_FAILED

@pytest.mark.asyncio
async def test_security_event_user_delete(db_session: AsyncSession):
    """
    Test that deleting a User sets user_id to NULL in SecurityEvent (SET NULL).
    """
    user = User(
        user_name="testuser", 
        email="test@example.com", 
        password_hash="dummy_hash"
    )
    db_session.add(user)
    await db_session.commit()

    event = SecurityEvent(
        user_id=user.id,
        event_type=SecurityEventType.PASSWORD_CHANGED,
    )
    db_session.add(event)
    await db_session.commit()

    event_id = event.id
    await db_session.delete(user)
    await db_session.commit()

    result = await db_session.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    saved_event = result.scalar_one()
    assert saved_event.user_id is None
