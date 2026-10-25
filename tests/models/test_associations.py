import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.associations.organization_user import OrganizationUser
from app.models.associations.user_role import UserRole

@pytest.mark.asyncio
async def test_organization_user_association(db_session: AsyncSession):
    """
    Test association between User and Organization.
    """
    user = User(
        user_name="member", 
        email="member@example.com", 
        password_hash="dummy_hash"
    )
    org = Organization(name="Org", slug="org-slug")
    db_session.add_all([user, org])
    await db_session.commit()

    membership = OrganizationUser(
        user_id=user.id,
        organization_id=org.id,
        is_active=True,
    )
    db_session.add(membership)
    await db_session.commit()

    assert membership.id is not None
    assert membership.user_id == user.id
    assert membership.organization_id == org.id

@pytest.mark.asyncio
async def test_organization_user_unique_constraint(db_session: AsyncSession):
    """
    Test that a user cannot be added to the same organization twice.
    """
    user = User(
        user_name="member", 
        email="member@example.com", 
        password_hash="dummy_hash"
    )
    org = Organization(name="Org", slug="org-slug")
    db_session.add_all([user, org])
    await db_session.commit()

    membership1 = OrganizationUser(user_id=user.id, organization_id=org.id)
    db_session.add(membership1)
    await db_session.commit()

    membership2 = OrganizationUser(user_id=user.id, organization_id=org.id)
    db_session.add(membership2)
    
    with pytest.raises(Exception): # SQLAlchemy IntegrityError
        await db_session.commit()

@pytest.mark.asyncio
async def test_user_role_association(db_session: AsyncSession):
    """
    Test association between User, Role, and Organization.
    """
    user = User(
        user_name="user", 
        email="user@example.com", 
        password_hash="dummy_hash"
    )
    org = Organization(name="Org", slug="org-slug")
    role = Role(name="Admin")
    db_session.add_all([user, org, role])
    await db_session.commit()

    ur = UserRole(
        user_id=user.id,
        role_id=role.id,
        organization_id=org.id,
    )
    db_session.add(ur)
    await db_session.commit()

    assert ur.id is not None
    assert ur.user_id == user.id
    assert ur.role_id == role.id
    assert ur.organization_id == org.id

@pytest.mark.asyncio
async def test_user_role_unique_constraint(db_session: AsyncSession):
    """
    Test that a user cannot have the same role in the same organization twice.
    """
    user = User(
        user_name="user", 
        email="user@example.com", 
        password_hash="dummy_hash"
    )
    org = Organization(name="Org", slug="org-slug")
    role = Role(name="Admin")
    db_session.add_all([user, org, role])
    await db_session.commit()

    ur1 = UserRole(user_id=user.id, role_id=role.id, organization_id=org.id)
    db_session.add(ur1)
    await db_session.commit()

    ur2 = UserRole(user_id=user.id, role_id=role.id, organization_id=org.id)
    db_session.add(ur2)
    
    with pytest.raises(Exception): # SQLAlchemy IntegrityError
        await db_session.commit()
