import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations.role_permission import RolePermission

@pytest.mark.asyncio
async def test_role_creation(db_session: AsyncSession):
    """
    Test basic Role model creation.
    """
    role = Role(
        name="Manager",
        description="Organization Manager",
        is_system=False,
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    assert role.id is not None
    assert role.name == "Manager"
    assert role.is_system is False

@pytest.mark.asyncio
async def test_role_unique_name(db_session: AsyncSession):
    """
    Test that Role names must be unique.
    """
    role1 = Role(name="UniqueRole")
    db_session.add(role1)
    await db_session.commit()

    role2 = Role(name="UniqueRole")
    db_session.add(role2)
    
    with pytest.raises(Exception): # SQLAlchemy IntegrityError
        await db_session.commit()

@pytest.mark.asyncio
async def test_role_permissions_association(db_session: AsyncSession):
    """
    Test associating roles with permissions.
    """
    role = Role(name="SuperAdmin")
    perm = Permission(name="AllAccess", code=1)
    db_session.add_all([role, perm])
    await db_session.commit()

    rp = RolePermission(role_id=role.id, permission_id=perm.id)
    db_session.add(rp)
    await db_session.commit()

    result = await db_session.execute(
        select(Role).where(Role.id == role.id).options(selectinload(Role.role_permissions))
    )
    saved_role = result.scalar_one()
    assert any(rp.permission_id == perm.id for rp in saved_role.role_permissions)
