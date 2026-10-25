import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.recovery_code import RecoveryCode
from app.models.user import User

@pytest.mark.asyncio
async def test_recovery_code_creation(db_session: AsyncSession):
    """
    Test basic RecoveryCode model creation.
    """
    user = User(
        user_name="testuser", 
        email="test@example.com", 
        password_hash="dummy_hash"
    )
    db_session.add(user)
    await db_session.commit()

    code = RecoveryCode(
        user_id=user.id,
        code_hash="hashed_code_123",
    )
    db_session.add(code)
    await db_session.commit()

    assert code.id is not None
    assert code.user_id == user.id
    assert code.code_hash == "hashed_code_123"
    assert code.used_at is None

@pytest.mark.asyncio
async def test_recovery_code_usage(db_session: AsyncSession):
    """
    Test marking a recovery code as used.
    """
    user = User(
        user_name="testuser", 
        email="test@example.com", 
        password_hash="dummy_hash"
    )
    db_session.add(user)
    await db_session.commit()

    code = RecoveryCode(user_id=user.id, code_hash="hashed_code_123")
    db_session.add(code)
    await db_session.commit()

    from datetime import datetime, UTC
    code.used_at = datetime.now(UTC)
    await db_session.commit()

    assert code.used_at is not None

@pytest.mark.asyncio
async def test_recovery_code_cascade_delete(db_session: AsyncSession):
    """
    Test that deleting a User deletes their recovery codes.
    """
    user = User(
        user_name="testuser", 
        email="test@example.com", 
        password_hash="dummy_hash"
    )
    db_session.add(user)
    await db_session.commit()

    code = RecoveryCode(user_id=user.id, code_hash="hashed_code_123")
    db_session.add(code)
    await db_session.commit()

    code_id = code.id
    await db_session.delete(user)
    await db_session.commit()

    result = await db_session.execute(select(RecoveryCode).where(RecoveryCode.id == code_id))
    assert result.scalar_one_or_none() is None
