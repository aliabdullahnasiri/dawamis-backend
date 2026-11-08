from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    Organization,
    OrganizationUser,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.services.permission import PermissionService
from tests.api.test_organizations import create


async def role_create(client, path, name="Pharmacist"):
    response = await client.post(
        path + "/roles", json={"name": name, "description": "Dispenses medicine"}
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_role_and_permission_lifecycle(client, identity, db_session):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    response = await client.get(path + "/permissions")
    assert response.status_code == 200, response.text
    catalog = {p["name"] for p in response.json()["data"]}
    assert {
        "medicine:create",
        "medicine:read",
        "supplier:delete",
        "purchase:cancel",
        "invoice:cancel",
        "customer:update",
    } <= catalog
    role = await role_create(client, path)
    role_path = path + f"/roles/{role['uuid']}"
    assert role["organization_id"] == org["id"]
    assert role["is_system"] is False
    assert (await client.get(role_path)).json()["data"] == role
    assert [r["id"] for r in (await client.get(path + "/roles")).json()["data"]] == [
        role["id"]
    ]
    assert (await client.get(role_path + "/permissions")).json()["data"] == []

    response = await client.put(
        role_path + "/permissions",
        json={"permissions": ["medicine:read", "medicine:create", "medicine:read"]},
    )
    assert response.status_code == 200, response.text
    assert [p["name"] for p in response.json()["data"]] == [
        "medicine:create",
        "medicine:read",
    ]
    assert (await client.get(role_path + "/permissions")).json() == response.json()
    response = await client.patch(
        role_path, json={"name": "Cashier", "description": None}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Cashier"
    assert response.json()["data"]["description"] is None
    assert (
        await client.put(role_path + "/permissions", json={"permissions": []})
    ).json()["data"] == []
    response = await client.delete(role_path)
    assert response.status_code == 204 and not response.content
    assert (await client.get(role_path)).status_code == 404
    assert await db_session.get(Role, role["id"]) is None
    assert (await db_session.scalars(select(RolePermission))).all() == []


@pytest.mark.asyncio
async def test_role_names_are_unique_per_organization(client, identity):
    org = await create(client)
    other = await create(client, "other")
    path = f"/api/v1/organizations/{org['uuid']}"
    await role_create(client, path, "Staff")
    assert (
        await client.post(path + "/roles", json={"name": "Staff"})
    ).status_code == 409
    await role_create(client, f"/api/v1/organizations/{other['uuid']}", "Staff")
    role = await role_create(client, path, "Manager")
    response = await client.patch(
        path + f"/roles/{role['uuid']}", json={"name": "Staff"}
    )
    assert response.status_code == 409, response.text
    assert len((await client.get(path + "/roles")).json()["data"]) == 2
    assert len((await client.get(path + "/roles?limit=1&offset=1")).json()["data"]) == 1


@pytest.mark.asyncio
async def test_role_and_membership_tenant_boundaries(client, identity):
    org = await create(client)
    other = await create(client, "other")
    path = f"/api/v1/organizations/{org['uuid']}"
    other_path = f"/api/v1/organizations/{other['uuid']}"
    role = await role_create(client, other_path)
    role_path = path + f"/roles/{role['uuid']}"
    for method, suffix, body in (
        ("GET", "", None),
        ("PATCH", "", {"name": "Intruder"}),
        ("DELETE", "", None),
        ("GET", "/permissions", None),
        ("PUT", "/permissions", {"permissions": []}),
    ):
        response = await client.request(method, role_path + suffix, json=body)
        assert response.status_code == 404, response.text
    member = (await client.get(path + "/members")).json()["data"][0]
    member_path = path + f"/members/{member['uuid']}/roles"
    assert (
        await client.put(member_path, json={"role_uuids": [role["uuid"]]})
    ).status_code == 404
    foreign_member_path = other_path + f"/members/{member['uuid']}/roles"
    assert (await client.get(foreign_member_path)).status_code == 404
    assert (
        await client.put(foreign_member_path, json={"role_uuids": []})
    ).status_code == 404


@pytest.mark.asyncio
async def test_assignment_replace_and_delete_cleanup(client, identity, db_session):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    first = await role_create(client, path, "First")
    second = await role_create(client, path, "Second")
    member = (await client.get(path + "/members")).json()["data"][0]
    member_path = path + f"/members/{member['uuid']}/roles"
    for roles in ([first["uuid"], first["uuid"]], [second["uuid"]], []):
        response = await client.put(member_path, json={"role_uuids": roles})
        assert response.status_code == 200, response.text
        assert {r["uuid"] for r in response.json()["data"]} == set(roles)
        assert (await client.get(member_path)).json() == response.json()
    await client.put(member_path, json={"role_uuids": [first["uuid"]]})
    assert (await client.delete(path + f"/roles/{first['uuid']}")).status_code == 204
    assert (await client.get(member_path)).json()["data"] == []
    assert (await db_session.scalars(select(UserRole))).all() == []


@pytest.mark.asyncio
async def test_unknown_permissions_do_not_replace_existing_grants(client, identity):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    await client.get(path + "/permissions")
    role = await role_create(client, path)
    permission_path = path + f"/roles/{role['uuid']}/permissions"
    await client.put(permission_path, json={"permissions": ["medicine:read"]})
    response = await client.put(
        permission_path, json={"permissions": ["invented:permission"]}
    )
    assert response.status_code == 422, response.text
    assert [p["name"] for p in (await client.get(permission_path)).json()["data"]] == [
        "medicine:read"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"name": " "},
        {"name": "x" * 51},
        {"name": "Staff", "is_system": True},
        {"name": "Staff", "organization_id": 1},
    ],
)
async def test_invalid_create_requests(client, identity, payload):
    org = await create(client)
    response = await client.post(
        f"/api/v1/organizations/{org['uuid']}/roles", json=payload
    )
    assert response.status_code == 433, response.text


@pytest.mark.asyncio
async def test_invalid_update_and_permission_requests(client, identity):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    role = await role_create(client, path)
    role_path = path + f"/roles/{role['uuid']}"
    for body in (
        {"name": None},
        {"name": ""},
        {"is_system": True},
        {"description": "x" * 256},
    ):
        assert (await client.patch(role_path, json=body)).status_code == 433
    for body in (
        {},
        {"permissions": None},
        {"permissions": [""]},
        {"permissions": "medicine:read"},
    ):
        assert (
            await client.put(role_path + "/permissions", json=body)
        ).status_code == 433
    assert (await client.get(path + f"/roles/{uuid4()}")).status_code == 404
    assert (await client.get(path + "/roles/invalid")).status_code == 433


@pytest.mark.asyncio
async def test_system_roles_are_protected(client, identity, db_session):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    role = Role(name="System", organization_id=org["id"], is_system=True)
    db_session.add(role)
    await db_session.commit()
    role_path = path + f"/roles/{role.uuid}"
    assert (await client.get(role_path)).status_code == 200
    assert (await client.patch(role_path, json={"name": "Changed"})).status_code == 409
    assert (
        await client.put(role_path + "/permissions", json={"permissions": []})
    ).status_code == 409
    assert (await client.delete(role_path)).status_code == 409


@pytest.mark.asyncio
async def test_rbac_requires_membership_and_operation_permission(
    client, identity, db_session
):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    role = await role_create(client, path)
    member = (await client.get(path + "/members")).json()["data"][0]
    organization = await db_session.get(Organization, org["id"])
    organization.owner_id = None
    await db_session.commit()
    operations = [
        ("GET", "/roles", None),
        ("POST", "/roles", {"name": "Denied"}),
        ("GET", f"/roles/{role['uuid']}", None),
        ("PATCH", f"/roles/{role['uuid']}", {"name": "Denied"}),
        ("DELETE", f"/roles/{role['uuid']}", None),
        ("GET", "/permissions", None),
        ("GET", f"/roles/{role['uuid']}/permissions", None),
        ("PUT", f"/roles/{role['uuid']}/permissions", {"permissions": []}),
        ("GET", f"/members/{member['uuid']}/roles", None),
        ("PUT", f"/members/{member['uuid']}/roles", {"role_uuids": []}),
    ]
    for method, suffix, body in operations:
        assert (
            await client.request(method, path + suffix, json=body)
        ).status_code == 403
    membership = await db_session.get(OrganizationUser, member["id"])
    membership.is_active = False
    await db_session.commit()
    assert (await client.get(path + "/roles")).status_code == 404
    del client.headers["Authorization"]
    for method, suffix, body in operations:
        assert (
            await client.request(method, path + suffix, json=body)
        ).status_code == 401


@pytest.mark.asyncio
async def test_delegate_cannot_escalate_permissions_or_assign_privileged_role(
    client, identity, db_session
):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    await client.get(path + "/permissions")
    admin = await role_create(client, path, "Delegated admin")
    powerful = await role_create(client, path, "Powerful")
    admin_permissions = ["roles:read", "roles:assign", "roles:permissions:update"]
    await client.put(
        path + f"/roles/{admin['uuid']}/permissions",
        json={"permissions": admin_permissions},
    )
    await client.put(
        path + f"/roles/{powerful['uuid']}/permissions",
        json={"permissions": ["medicine:delete"]},
    )
    member = (await client.get(path + "/members")).json()["data"][0]
    member_path = path + f"/members/{member['uuid']}/roles"
    await client.put(member_path, json={"role_uuids": [admin["uuid"]]})
    organization = await db_session.get(Organization, org["id"])
    organization.owner_id = None
    await db_session.commit()
    assert (await client.get(path + "/roles")).status_code == 200
    response = await client.put(
        path + f"/roles/{admin['uuid']}/permissions",
        json={"permissions": admin_permissions + ["medicine:delete"]},
    )
    assert response.status_code == 403, response.text
    assert (
        await client.put(member_path, json={"role_uuids": [powerful["uuid"]]})
    ).status_code == 403
    assert [r["uuid"] for r in (await client.get(member_path)).json()["data"]] == [
        admin["uuid"]
    ]
    # A delegate can grant permissions they actually have.
    response = await client.put(
        path + f"/roles/{powerful['uuid']}/permissions",
        json={"permissions": ["roles:read"]},
    )
    assert response.status_code == 200, response.text
    assert (
        await client.put(
            member_path, json={"role_uuids": [admin["uuid"], powerful["uuid"]]}
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_inactive_members_cannot_receive_roles(client, identity, db_session):
    org = await create(client)
    user = User(
        user_name="inactive", email="inactive@example.com", password_hash="unused"
    )
    db_session.add(user)
    await db_session.flush()
    member = OrganizationUser(
        organization_id=org["id"], user_id=user.id, is_active=False
    )
    db_session.add(member)
    await db_session.commit()
    response = await client.put(
        f"/api/v1/organizations/{org['uuid']}/members/{member.uuid}/roles",
        json={"role_uuids": []},
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_cached_permissions_are_revoked_through_api(
    client, identity, db_session, mock_redis
):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    await client.get(path + "/permissions")
    role = await role_create(client, path)
    role_path = path + f"/roles/{role['uuid']}"
    await client.put(
        role_path + "/permissions",
        json={"permissions": ["roles:read", "roles:permissions:update"]},
    )
    member = (await client.get(path + "/members")).json()["data"][0]
    await client.put(
        path + f"/members/{member['uuid']}/roles", json={"role_uuids": [role["uuid"]]}
    )
    organization = await db_session.get(Organization, org["id"])
    organization.owner_id = None
    await db_session.commit()
    assert (await client.get(path + "/roles")).status_code == 200
    assert await mock_redis.keys("rbac:permissions:*")
    assert (
        await client.put(role_path + "/permissions", json={"permissions": []})
    ).status_code == 200
    assert (await client.get(path + "/roles")).status_code == 403
    assert (
        await PermissionService.granted(
            db_session, identity[0].id, org["id"], mock_redis
        )
        == set()
    )
