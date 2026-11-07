from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies.auth import current_user_can
from app.models import (
    OrganizationMembership,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserSession,
)
from app.services.auth.jwt import JWTService
from app.services.datetime import DateTimeService


@pytest_asyncio.fixture
async def identity(client, db_session):
    user = User(
        user_name="org-owner", email="owner@example.com", password_hash="unused"
    )
    db_session.add(user)
    await db_session.flush()
    session = UserSession(
        user=user,
        ip_address="127.0.0.1",
        user_agent=client.headers["user-agent"],
        expires_at=DateTimeService.utc_now() + timedelta(days=1),
    )
    db_session.add(session)
    await db_session.commit()
    client.headers["Authorization"] = (
        f"Bearer {JWTService.create_access_token(user.uuid)}"
    )
    return user, session


async def create(client, slug="pharmacy"):
    response = await client.post(
        "/api/v1/organizations",
        json={"name": "Pharmacy", "slug": slug, "settings": {"currency": "AFN"}},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_lifecycle(client, identity, db_session):
    user, session = identity
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    assert org["owner_id"] == user.id
    assert org["settings"] == {"currency": "AFN"}
    assert org["created_at"] and org["updated_at"]
    assert (await client.get(path)).status_code == 200
    assert len((await client.get("/api/v1/organizations")).json()["data"]) == 1
    members = (await client.get(path + "/members")).json()["data"]
    assert members[0]["user_id"] == user.id
    assert (
        await client.delete(path + f"/members/{members[0]['uuid']}")
    ).status_code == 409
    response = await client.post(f"/api/v1/auth/organizations/{org['uuid']}/select")
    assert response.status_code == 200, response.text
    assert (await client.get("/api/v1/auth/organization")).json()["data"]["id"] == org[
        "id"
    ]
    assert session.organization_id == org["id"]
    refreshed = await client.post(
        "/api/v1/auth/refresh",
        headers={
            "Authorization": f"Bearer {JWTService.create_refresh_token(user.uuid)}"
        },
    )
    assert refreshed.status_code == 200, refreshed.text
    client.headers["Authorization"] = (
        f"Bearer {refreshed.json()['data']['access_token']}"
    )
    assert (await client.get("/api/v1/auth/organization")).json()["data"]["id"] == org[
        "id"
    ]
    assert (await client.patch(path, json={"name": "Updated", "settings": {}})).json()[
        "data"
    ]["name"] == "Updated"
    assert (await client.patch(path, json={"is_active": False})).status_code == 200
    assert (await client.get("/api/v1/auth/organization")).status_code == 403
    assert (
        await client.post(f"/api/v1/auth/organizations/{org['uuid']}/select")
    ).status_code == 403
    assert (await client.patch(path, json={"is_active": True})).status_code == 200
    response = await client.delete(path)
    assert response.status_code == 204 and not response.content
    assert session.organization_id is None
    assert (await client.get(path)).status_code == 404


@pytest.mark.asyncio
async def test_membership_and_isolation(client, identity, db_session):
    org = await create(client)
    other = await create(client, "other")
    path = f"/api/v1/organizations/{org['uuid']}"
    outsider = User(
        user_name="outsider", email="outsider@example.com", password_hash="unused"
    )
    db_session.add(outsider)
    await db_session.commit()
    response = await client.post(path + "/members", json={"user_id": outsider.id})
    assert response.status_code == 201, response.text
    member_uuid = response.json()["data"]["uuid"]
    assert (
        await client.patch(
            f"/api/v1/organizations/{other['uuid']}/members/{member_uuid}",
            json={"is_active": False},
        )
    ).status_code == 404
    assert (
        await client.patch(path + f"/members/{member_uuid}", json={"is_active": False})
    ).status_code == 200
    assert (await client.patch(path, json={"owner_id": outsider.id})).status_code == 404
    assert (
        await client.patch(path + f"/members/{member_uuid}", json={"is_active": True})
    ).status_code == 200
    assert (await client.patch(path, json={"owner_id": outsider.id})).status_code == 200
    assert (await client.patch(path, json={"name": "Denied"})).status_code == 403
    assert (await client.delete(path)).status_code == 403


@pytest.mark.asyncio
async def test_permission_scope_and_revocation(client, identity, db_session, app):
    user, session = identity
    org = await create(client)
    other = await create(client, "other")
    permission = Permission(name="stock.read", code=1)
    role = Role(name="reader")
    db_session.add_all([permission, role])
    await db_session.flush()
    db_session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
            UserRole(user_id=user.id, role_id=role.id, organization_id=org["id"]),
        ]
    )
    await db_session.commit()

    async def protected():
        return {"ok": True}

    app.add_api_route(
        "/test-org-permission",
        protected,
        dependencies=[Depends(current_user_can("stock.read"))],
    )
    app.add_api_route(
        "/test-org-all",
        protected,
        dependencies=[Depends(current_user_can("stock.read", "stock.write"))],
    )
    try:
        assert (await client.get("/test-org-permission")).status_code == 403
        await client.post(f"/api/v1/auth/organizations/{org['uuid']}/select")
        assert (await client.get("/test-org-permission")).status_code == 200
        assert (await client.get("/test-org-all")).status_code == 403
        await client.post(f"/api/v1/auth/organizations/{other['uuid']}/select")
        assert (await client.get("/test-org-permission")).status_code == 403
        await client.post(f"/api/v1/auth/organizations/{org['uuid']}/select")
        member = await db_session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org["id"]
            )
        )
        member.is_active = False
        await db_session.commit()
        assert (await client.get("/test-org-permission")).status_code == 404
        session.revoked_at = DateTimeService.utc_now()
        await db_session.commit()
        assert (await client.get("/api/v1/organizations")).status_code == 401
    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", "")
            not in {"/test-org-permission", "/test-org-all"}
        ]


@pytest.mark.asyncio
async def test_invalid_input_and_token_types(client, identity, db_session):
    org = await create(client)
    assert (
        await client.post(
            "/api/v1/organizations", json={"name": "Duplicate", "slug": "pharmacy"}
        )
    ).status_code == 409
    for payload in ({"name": " "}, {"settings": None}, {"slug": "Bad Slug"}):
        assert (
            await client.patch(f"/api/v1/organizations/{org['uuid']}", json=payload)
        ).status_code == 433
    assert (await client.delete("/api/v1/users/me")).status_code == 409
    user, _ = identity
    client.headers["Authorization"] = (
        f"Bearer {JWTService.create_refresh_token(user.uuid)}"
    )
    assert (await client.get("/api/v1/organizations")).status_code == 401
    token = JWTService.create_access_token(user.uuid)
    await JWTService.revoke(token, db_session)
    client.headers["Authorization"] = f"Bearer {token}"
    assert (await client.get("/api/v1/organizations")).status_code == 401
    del client.headers["Authorization"]
    assert (await client.get("/api/v1/organizations")).status_code == 401


@pytest.mark.asyncio
async def test_outsider_and_member_removal(client, identity, db_session):
    _, session = identity
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}"
    stranger = User(
        user_name="stranger", email="stranger@example.com", password_hash="unused"
    )
    db_session.add(stranger)
    await db_session.flush()
    stranger_session = UserSession(
        user=stranger,
        ip_address="127.0.0.1",
        user_agent=client.headers["user-agent"],
        expires_at=DateTimeService.utc_now() + timedelta(days=1),
    )
    db_session.add(stranger_session)
    await db_session.commit()
    owner_token = client.headers["Authorization"]
    client.headers["Authorization"] = (
        f"Bearer {JWTService.create_access_token(stranger.uuid)}"
    )
    assert (await client.get("/api/v1/organizations")).json()["data"] == []
    assert (await client.get(path)).status_code == 404
    assert (await client.get(path + "/members")).status_code == 404
    assert (
        await client.post(f"/api/v1/auth/organizations/{org['uuid']}/select")
    ).status_code == 404
    client.headers["Authorization"] = owner_token
    member = (
        await client.post(path + "/members", json={"user_id": stranger.id})
    ).json()["data"]
    role = Role(name="removed-role")
    db_session.add(role)
    await db_session.flush()
    db_session.add(
        UserRole(user_id=stranger.id, role_id=role.id, organization_id=org["id"])
    )
    stranger_session.organization_id = org["id"]
    await db_session.commit()
    assert session.organization_id is None
    assert (await client.delete(path + f"/members/{member['uuid']}")).status_code == 204
    assert stranger_session.organization_id is None
    assert (
        await db_session.scalar(select(UserRole).where(UserRole.user_id == stranger.id))
        is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identifier, expected",
    [("123", 433), ("not-a-uuid", 433), ("00000000-0000-0000-0000-000000000001", 404)],
)
async def test_organization_uuid_paths(client, identity, identifier, expected):
    path = f"/api/v1/organizations/{identifier}"
    for method, url, payload in (
        ("GET", path, None),
        ("PATCH", path, {"name": "Updated"}),
        ("DELETE", path, None),
        ("GET", path + "/members", None),
        ("POST", path + "/members", {"user_id": identity[0].id}),
        ("POST", f"/api/v1/auth/organizations/{identifier}/select", None),
    ):
        response = await client.request(method, url, json=payload)
        assert response.status_code == expected, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identifier, expected",
    [("123", 433), ("not-a-uuid", 433), ("00000000-0000-0000-0000-000000000001", 404)],
)
async def test_membership_uuid_paths(client, identity, identifier, expected):
    org = await create(client)
    path = f"/api/v1/organizations/{org['uuid']}/members/{identifier}"
    response = await client.patch(path, json={"is_active": False})
    assert response.status_code == expected, response.text
    response = await client.delete(path)
    assert response.status_code == expected, response.text


def test_resource_paths_use_uuid_parameters(app):
    for path, operations in app.openapi()["paths"].items():
        for operation in operations.values():
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path":
                    assert parameter["name"].endswith("_uuid"), path
                    assert parameter["schema"]["format"] == "uuid", path
