from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

@pytest.mark.asyncio
async def test_user_password_hashing(db_session: AsyncSession):
    """
    Test that passwords are correctly hashed and verified.
    """
    password = "secure_password_123"
    user = User(
        user_name="testuser",
        email="test@example.com",
    )
    user.set_password(password)

    # Verify that password_hash is set and not plain text
    assert user.password_hash is not None
    assert user.password_hash != password

    # Test password verification
    assert user.check_password(password) is True
    assert user.check_password("wrong_password") is False

@pytest.mark.asyncio
async def test_user_creation(db_session: AsyncSession):
    """
    Test basic User model creation and field assignment.
    """
    user = User(
        first_name="John",
        last_name="Doe",
        user_name="johndoe",
        email="john@example.com",
    )
    user.set_password("password123")

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.user_name == "johndoe"
    assert user.email == "john@example.com"
    assert user.first_name == "John"
    assert user.last_name == "Doe"

@pytest.mark.asyncio
async def test_user_birthday(db_session: AsyncSession):
    """
    Test that birthday field is correctly handled.
    """
    birthday = date(1990, 1, 1)
    user = User(
        user_name="bdayuser",
        email="bday@example.com",
        birthday=birthday,
    )
    user.set_password("password123")

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.birthday == birthday
