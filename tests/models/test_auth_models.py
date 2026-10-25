import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations.role_permission import RolePermission
from app.models.user import User
from app.models.associations.user_role import UserRole
from app.models.organization import Organization

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

from sqlalchemy import select
from sqlalchemy.orm import selectinload

@pytest.mark.asyncio
async def test_role_and_permissions(db_session: AsyncSession):
    """
    Test Role creation and its association with Permissions.
    """
    role = Role(
        name="Admin",
        description="Administrator role",
        is_system=False,
    )
    perm1 = Permission(name="Perm 1", code=1)
    perm2 = Permission(name="Perm 2", code=2)

    db_session.add_all([role, perm1, perm2])
    await db_session.commit()

    # Associate permissions with role
    rp1 = RolePermission(role_id=role.id, permission_id=perm1.id)
    rp2 = RolePermission(role_id=role.id, permission_id=perm2.id)
    db_session.add_all([rp1, rp2])
    await db_session.commit()

    # Eagerly load permissions to avoid MissingGreenlet
    result = await db_session.execute(
        select(Role).where(Role.id == role.id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one()

    assert len(role.permissions) == 2
    assert any(p.code == 1 for p in role.permissions)
    assert any(p.code == 2 for p in role.permissions)

@pytest.mark.asyncio
async def test_user_role_assignment(db_session: AsyncSession):
    """
    Test assigning a Role to a User within an Organization.
    """
    user = User(user_name="roleuser", email="role@example.com")
    user.set_password("password")
    org = Organization(name="Org", slug="org-slug")
    role = Role(name="Manager")

    db_session.add_all([user, org, role])
    await db_session.commit()

    # Assign role to user in org
    ur = UserRole(
        user_id=user.id,
        role_id=role.id,
        organization_id=org.id,
    )
    db_session.add(ur)
    await db_session.commit()

    # Eagerly load user_roles to avoid MissingGreenlet
    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.user_roles))
    )
    user = result.scalar_one()

    assert len(user.user_roles) == 1
    assert user.user_roles[0].role_id == role.id
    assert user.user_roles[0].organization_id == org.id
