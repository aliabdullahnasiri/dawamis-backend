import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.permission import Permission
from app.models.role import Role
from app.models.associations.role_permission import RolePermission

@pytest.mark.asyncio
async def test_permission_creation(db_session: AsyncSession):
    """
    Test basic Permission model creation.
    """
    perm = Permission(
        name="Edit User",
        description="Allows editing users",
        code=101,
    )
    db_session.add(perm)
    await db_session.commit()
    await db_session.refresh(perm)

    assert perm.id is not None
    assert perm.name == "Edit User"
    assert perm.code == 101

@pytest.mark.asyncio
async def test_permission_unique_name(db_session: AsyncSession):
    """
    Test that Permission names must be unique.
    """
    perm1 = Permission(name="Unique", code=1)
    db_session.add(perm1)
    await db_session.commit()

    perm2 = Permission(name="Unique", code=2)
    db_session.add(perm2)
    
    with pytest.raises(Exception): # SQLAlchemy IntegrityError
        await db_session.commit()

@pytest.mark.asyncio
async def test_permission_role_association(db_session: AsyncSession):
    """
    Test associating permissions with roles.
    """
    role = Role(name="Admin")
    perm = Permission(name="AdminPerm", code=10)
    db_session.add_all([role, perm])
    await db_session.commit()

    rp = RolePermission(role_id=role.id, permission_id=perm.id)
    db_session.add(rp)
    await db_session.commit()

    result = await db_session.execute(
        select(Permission).where(Permission.id == perm.id).options(selectinload(Permission.role_permissions))
    )
    saved_perm = result.scalar_one()
    assert any(rp.role_id == role.id for rp in saved_perm.role_permissions)
