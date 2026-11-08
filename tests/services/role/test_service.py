from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.exceptions import ConnectionError
from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Role, RolePermission, User, UserRole
from app.services.organization import OrganizationService
from app.services.permission import PermissionService
from app.services.role import RoleService


@pytest_asyncio.fixture
async def setup_roles(db_session):
    owner = User(
        user_name="owner", email="role-owner@example.com", password_hash="unused"
    )
    member = User(
        user_name="member", email="role-member@example.com", password_hash="unused"
    )
    db_session.add_all([owner, member])
    await db_session.flush()
    org = await OrganizationService.create(db_session, "Pharmacy", "pharmacy", owner)
    membership = await OrganizationService.add_member(db_session, org.id, member.id)
    await PermissionService.list_definitions(db_session)
    role = await RoleService.create(db_session, org.id, "Staff", "Description")
    await RoleService.set_permissions(
        db_session, org.id, role.uuid, ["medicine:read"], owner.id
    )
    await RoleService.set_member_roles(
        db_session, org.id, membership.uuid, [role.uuid], owner.id
    )
    return owner, member, org, membership, role


@pytest.mark.asyncio
async def test_service_lifecycle_and_conflicts(db_session, setup_roles):
    owner, _, org, membership, role = setup_roles
    assert (await RoleService.get(db_session, org.id, role.uuid)).name == "Staff"
    assert await RoleService.list(db_session, org.id) == [role]
    with pytest.raises(ConflictError):
        await RoleService.create(db_session, org.id, "Staff")
    with pytest.raises(NotFoundError):
        await RoleService.get(db_session, org.id, uuid4())
    with pytest.raises(ValidationError):
        await RoleService.set_permissions(
            db_session, org.id, role.uuid, ["unknown"], owner.id
        )
    assert [
        p.name for p in await RoleService.permissions(db_session, org.id, role.uuid)
    ] == ["medicine:read"]
    updated = await RoleService.update(
        db_session, org.id, role.uuid, {"name": "Updated", "description": None}
    )
    assert updated.name == "Updated" and updated.description is None
    await RoleService.delete(db_session, org.id, role.uuid)
    assert await RoleService.member_roles(db_session, org.id, membership.uuid) == []
    assert (await db_session.scalars(select(RolePermission))).all() == []
    assert (await db_session.scalars(select(UserRole))).all() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", ["permissions", "assignment", "delete", "remove_member"]
)
async def test_grant_changes_invalidate_warm_cache(
    db_session, setup_roles, mock_redis, change
):
    owner, member, org, membership, role = setup_roles
    assert await PermissionService.granted(
        db_session, member.id, org.id, mock_redis
    ) == {"medicine:read"}
    old_version = org.rbac_version
    if change == "permissions":
        await RoleService.set_permissions(db_session, org.id, role.uuid, [], owner.id)
    elif change == "assignment":
        await RoleService.set_member_roles(
            db_session, org.id, membership.uuid, [], owner.id
        )
    elif change == "delete":
        await RoleService.delete(db_session, org.id, role.uuid)
    else:
        await OrganizationService.remove_member(db_session, org.id, member.id)
        await OrganizationService.add_member(db_session, org.id, member.id)
    assert org.rbac_version > old_version
    assert (
        await PermissionService.granted(db_session, member.id, org.id, mock_redis)
        == set()
    )


@pytest.mark.asyncio
async def test_cache_hit_avoids_grant_query_and_has_ttl(
    db_session, setup_roles, mock_redis, monkeypatch
):
    _, member, org, _, _ = setup_roles
    expected = {"medicine:read"}
    assert (
        await PermissionService.granted(db_session, member.id, org.id, mock_redis)
        == expected
    )
    key = (await mock_redis.keys("rbac:permissions:*"))[0]
    assert 0 < await mock_redis.ttl(key) <= 300
    query = AsyncMock(wraps=db_session.scalars)
    monkeypatch.setattr(db_session, "scalars", query)
    assert (
        await PermissionService.granted(db_session, member.id, org.id, mock_redis)
        == expected
    )
    query.assert_not_called()
    await mock_redis.delete(key)
    assert (
        await PermissionService.granted(db_session, member.id, org.id, mock_redis)
        == expected
    )
    query.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("cached", ["broken-json", "{}", "[1]", "null"])
async def test_corrupt_cache_falls_back_to_database(
    db_session, setup_roles, mock_redis, cached
):
    _, member, org, _, _ = setup_roles
    await PermissionService.granted(db_session, member.id, org.id, mock_redis)
    key = (await mock_redis.keys("rbac:permissions:*"))[0]
    await mock_redis.set(key, cached)
    assert await PermissionService.granted(
        db_session, member.id, org.id, mock_redis
    ) == {"medicine:read"}


@pytest.mark.asyncio
async def test_redis_failure_falls_back_to_database(db_session, setup_roles):
    _, member, org, _, _ = setup_roles
    redis = AsyncMock()
    redis.get.side_effect = ConnectionError("unavailable")
    redis.set.side_effect = ConnectionError("unavailable")
    assert await PermissionService.granted(db_session, member.id, org.id, redis) == {
        "medicine:read"
    }


@pytest.mark.asyncio
async def test_legacy_and_mismatched_roles_never_grant_access(
    db_session, setup_roles, mock_redis
):
    owner, member, org, _, role = setup_roles
    other = await OrganizationService.create(db_session, "Other", "other", owner)
    # Deliberately inject a malformed association, bypassing the assignment service.
    db_session.add(
        UserRole(user_id=member.id, role_id=role.id, organization_id=other.id)
    )
    legacy = Role(name="Legacy")
    db_session.add(legacy)
    await db_session.flush()
    permission_id = await db_session.scalar(
        select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
    )
    db_session.add_all(
        [
            RolePermission(role_id=legacy.id, permission_id=permission_id),
            UserRole(user_id=member.id, role_id=legacy.id, organization_id=other.id),
        ]
    )
    await db_session.commit()
    assert (
        await PermissionService.granted(db_session, member.id, other.id, mock_redis)
        == set()
    )
    assert await PermissionService.granted(
        db_session, member.id, org.id, mock_redis
    ) == {"medicine:read"}


@pytest.mark.asyncio
async def test_organization_deletion_cleans_roles(db_session, setup_roles):
    _, _, org, _, role = setup_roles
    role_id = role.id
    await OrganizationService.delete(db_session, org)
    assert await db_session.get(Role, role_id) is None
    assert (await db_session.scalars(select(RolePermission))).all() == []
    assert (await db_session.scalars(select(UserRole))).all() == []


@pytest.mark.asyncio
async def test_invalid_assignment_preserves_current_roles(db_session, setup_roles):
    owner, _, org, membership, role = setup_roles
    other = await OrganizationService.create(db_session, "Other", "other", owner)
    foreign_role = await RoleService.create(db_session, other.id, "Staff")
    version = org.rbac_version
    for invalid in (uuid4(), foreign_role.uuid):
        with pytest.raises(NotFoundError):
            await RoleService.set_member_roles(
                db_session, org.id, membership.uuid, [role.uuid, invalid], owner.id
            )
        assert await RoleService.member_roles(db_session, org.id, membership.uuid) == [
            role
        ]
        assert org.rbac_version == version


@pytest.mark.asyncio
async def test_cache_separates_users(db_session, setup_roles, mock_redis):
    owner, member, org, _, _ = setup_roles
    assert await PermissionService.granted(
        db_session, member.id, org.id, mock_redis
    ) == {"medicine:read"}
    # Owner bypass is evaluated outside the cache; no role grants are stored for them.
    assert (
        await PermissionService.granted(db_session, owner.id, org.id, mock_redis)
        == set()
    )
