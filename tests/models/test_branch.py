import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.models.organization import Organization


@pytest.mark.asyncio
async def test_branch_creation(db_session: AsyncSession):
    """
    Test basic Branch model creation and association with Organization.
    """
    org = Organization(name="Main Org", slug="main-org")
    db_session.add(org)
    await db_session.commit()

    branch = Branch(
        name="Downtown Branch",
        address="123 Main St",
        organization_id=org.id,
        is_active=True,
    )
    db_session.add(branch)
    await db_session.commit()

    assert branch.id is not None
    assert branch.name == "Downtown Branch"
    assert branch.organization_id == org.id

@pytest.mark.asyncio
async def test_branch_inactive(db_session: AsyncSession):
    """
    Test Branch creation with inactive status.
    """
    org = Organization(name="Org 2", slug="org2")
    db_session.add(org)
    await db_session.commit()

    branch = Branch(
        name="Closed Branch",
        organization_id=org.id,
        is_active=False,
    )
    db_session.add(branch)
    await db_session.commit()

    assert branch.is_active is False

@pytest.mark.asyncio
async def test_branch_cascade_delete(db_session: AsyncSession):
    """
    Test that deleting an Organization deletes its branches.
    """
    org = Organization(name="Delete Org", slug="delete-org")
    db_session.add(org)
    await db_session.commit()

    branch = Branch(name="Cascade Branch", organization_id=org.id)
    db_session.add(branch)
    await db_session.commit()

    branch_id = branch.id
    await db_session.delete(org)
    await db_session.commit()

    result = await db_session.execute(select(Branch).where(Branch.id == branch_id))
    assert result.scalar_one_or_none() is None
