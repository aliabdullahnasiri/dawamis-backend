import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.models.branch import Branch
from app.models.associations.organization_user import OrganizationUser
from app.models.user import User

@pytest.mark.asyncio
async def test_organization_creation(db_session: AsyncSession):
    """
    Test basic Organization model creation.
    """
    org = Organization(
        name="Test Org",
        slug="test-org",
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    assert org.id is not None
    assert org.name == "Test Org"
    assert org.slug == "test-org"
    assert org.is_active is True

from sqlalchemy import select
from sqlalchemy.orm import selectinload

@pytest.mark.asyncio
async def test_branch_creation(db_session: AsyncSession):
    """
    Test Branch creation and its relationship with Organization.
    """
    org = Organization(name="Org", slug="org-slug")
    db_session.add(org)
    await db_session.commit()

    branch = Branch(
        organization_id=org.id,
        name="Main Branch",
        address="123 Test St",
        is_active=True,
    )
    db_session.add(branch)
    await db_session.commit()
    await db_session.refresh(branch)

    assert branch.id is not None
    assert branch.organization_id == org.id
    assert branch.name == "Main Branch"

    # Eagerly load branches to avoid MissingGreenlet
    result = await db_session.execute(
        select(Organization).where(Organization.id == org.id).options(selectinload(Organization.branches))
    )
    org = result.scalar_one()
    assert len(org.branches) == 1
    assert org.branches[0].name == "Main Branch"

@pytest.mark.asyncio
async def test_organization_membership(db_session: AsyncSession):
    """
    Test the association between User and Organization.
    """
    user = User(user_name="memuser", email="mem@example.com")
    user.set_password("password")
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

    # Eagerly load memberships to avoid MissingGreenlet
    user_result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.organization_memberships))
    )
    user = user_result.scalar_one()

    org_result = await db_session.execute(
        select(Organization).where(Organization.id == org.id).options(selectinload(Organization.memberships))
    )
    org = org_result.scalar_one()

    assert len(user.organization_memberships) == 1
    assert len(org.memberships) == 1
    assert user.organization_memberships[0].organization_id == org.id
