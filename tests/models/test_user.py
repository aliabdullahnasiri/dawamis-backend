from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_user_permissions_relationship_and_mask(db_session: AsyncSession):
    user = User(
        user_name="permissions", email="permissions@example.com", password_hash="unused"
    )
    outsider = User(
        user_name="outsider", email="outsider@example.com", password_hash="unused"
    )
    organizations = [
        Organization(name="First", slug="first"),
        Organization(name="Second", slug="second"),
    ]
    roles = [Role(name="reader"), Role(name="writer"), Role(name="outsider")]
    permissions = [
        Permission(id=1, name="read"),
        Permission(id=2, name="ungranted"),
        Permission(id=3, name="write"),
    ]
    db_session.add_all([user, outsider, *organizations, *roles, *permissions])
    await db_session.flush()
    db_session.add_all(
        [
            UserRole(
                user_id=user.id,
                role_id=roles[0].id,
                organization_id=organizations[0].id,
            ),
            UserRole(
                user_id=user.id,
                role_id=roles[0].id,
                organization_id=organizations[1].id,
            ),
            UserRole(
                user_id=user.id,
                role_id=roles[1].id,
                organization_id=organizations[1].id,
            ),
            UserRole(
                user_id=outsider.id,
                role_id=roles[2].id,
                organization_id=organizations[0].id,
            ),
            RolePermission(role_id=roles[0].id, permission_id=1),
            RolePermission(role_id=roles[1].id, permission_id=1),
            RolePermission(role_id=roles[1].id, permission_id=3),
            RolePermission(role_id=roles[2].id, permission_id=2),
        ]
    )
    await db_session.commit()

    loaded = await db_session.scalar(select(User).where(User.id == user.id))
    assert loaded is not None
    assert [permission.name for permission in loaded.permissions] == ["read", "write"]
    assert loaded.permissions_mask == 0b101
    assert loaded.permissions_mask & (1 << (2 - 1)) == 0


@pytest.mark.asyncio
async def test_user_without_permissions_has_empty_mask(db_session: AsyncSession):
    user = User(
        user_name="no-permissions", email="none@example.com", password_hash="unused"
    )
    db_session.add(user)
    await db_session.commit()
    loaded = await db_session.scalar(select(User).where(User.id == user.id))
    assert loaded is not None
    assert loaded.permissions == []
    assert loaded.permissions_mask == 0


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
