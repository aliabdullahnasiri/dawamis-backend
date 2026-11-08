import json
from datetime import timedelta

import pytest
from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies.auth import current_user_can
from app.models import (
    Organization,
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
from app.services.jinja import JinjaService
from app.services.permission import PermissionService


async def create(client, slug="pharmacy"):
    response = await client.post(
        "/api/v1/organizations",
        json={"name": "Pharmacy", "slug": slug, "settings": {"currency": "AFN"}},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_join_request_emails_owner_without_granting_membership(
    client, identity, db_session, mock_mail
):
    requester, session = identity
    owner = User(
        user_name="recipient", email="recipient@example.com", password_hash="unused"
    )
    db_session.add(owner)
    await db_session.flush()
    organization = Organization(
        name="Requested pharmacy", slug="requested", owner_id=owner.id
    )
    db_session.add(organization)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/organizations/{organization.uuid}/join-requests"
    )
    assert response.status_code == 202, response.text
    mock_mail["send_template"].assert_called_once()
    message = mock_mail["send_template"].call_args.kwargs
    assert message["template"] == "emails/organization/join_request.html"
    assert message["user"] == {
        "id": requester.id,
        "user_name": requester.user_name,
        "email": requester.email,
    }
    assert message["to"] == owner.email
    assert message["subject"] == "Organization membership request"
    assert message["organization"] == {
        "name": organization.name,
        "uuid": str(organization.uuid),
    }
    assert requester.email in message["text"]
    assert organization.name in message["text"]
    assert "{username}" not in message["text"]
    assert json.loads(json.dumps(message)) == message
    html = JinjaService.render(
        message["template"],
        user=message["user"],
        organization={**message["organization"], "name": "<b>Pharmacy</b>"},
    )
    assert requester.email in html
    assert "&lt;b&gt;Pharmacy&lt;/b&gt;" in html
    assert "Organization membership request" in html
    assert "emails:organization_" not in html
    assert session.organization_id is None
    assert (
        await db_session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.user_id == requester.id,
            )
        )
        is None
    )
    assert (
        await client.post(f"/api/v1/auth/organizations/{organization.uuid}/select")
    ).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case, expected",
    [
        ("member", 409),
        ("inactive", 403),
        ("ownerless", 409),
        ("missing", 404),
        ("anonymous", 401),
    ],
)
async def test_join_request_rejections(
    client, identity, db_session, mock_mail, case, expected
):
    from uuid import uuid4

    organization = await create(client)
    target = await db_session.get(Organization, organization["id"])
    organization_uuid = target.uuid
    if case == "inactive":
        target.is_active = False
    elif case == "ownerless":
        target.owner_id = None
        membership = await db_session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == target.id
            )
        )
        await db_session.delete(membership)
    elif case == "missing":
        organization_uuid = uuid4()
    elif case == "anonymous":
        del client.headers["Authorization"]
    await db_session.commit()
    response = await client.post(
        f"/api/v1/organizations/{organization_uuid}/join-requests"
    )
    assert response.status_code == expected, response.text
    mock_mail["send"].assert_not_called()
    mock_mail["send_template"].assert_not_called()


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
    # Exercise role checks as a member rather than using the owner bypass.
    for organization_id in (org["id"], other["id"]):
        organization = await db_session.get(Organization, organization_id)
        organization.owner_id = None
    permission = Permission(name="stock.read")
    role = Role(name="reader", organization_id=org["id"])
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
        registered = (
            await db_session.scalars(
                select(Permission.name).where(
                    Permission.name.in_(("stock.read", "stock.write"))
                )
            )
        ).all()
        assert set(registered) == {"stock.read", "stock.write"}
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
async def test_member_management_checks_url_organization_permissions(
    client, identity, db_session
):
    user, _ = identity
    selected = await create(client, "selected")
    target = await create(client, "target")
    target_model = await db_session.get(Organization, target["id"])
    target_model.owner_id = None
    role = Role(name="member-manager", organization_id=selected["id"])
    permission = Permission(name="organizations.members.manage")
    candidate = User(
        user_name="candidate", email="candidate@example.com", password_hash="unused"
    )
    db_session.add_all([role, permission, candidate])
    await db_session.flush()
    db_session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
            UserRole(user_id=user.id, role_id=role.id, organization_id=selected["id"]),
        ]
    )
    await db_session.commit()
    await client.post(f"/api/v1/auth/organizations/{selected['uuid']}/select")
    path = f"/api/v1/organizations/{target['uuid']}/members"
    response = await client.post(path, json={"user_id": candidate.id})
    assert response.status_code == 403, response.text
    assert (
        await db_session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.organization_id == target["id"],
                OrganizationMembership.user_id == candidate.id,
            )
        )
        is None
    )

    target_role = Role(name="member-manager", organization_id=target["id"])
    db_session.add(target_role)
    await db_session.flush()
    db_session.add_all(
        [
            RolePermission(role_id=target_role.id, permission_id=permission.id),
            UserRole(
                user_id=user.id, role_id=target_role.id, organization_id=target["id"]
            ),
        ]
    )
    await PermissionService.invalidate(db_session, target["id"])
    await db_session.commit()
    response = await client.post(path, json={"user_id": candidate.id})
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suffix, permission_name",
    [("", "organizations.read"), ("/members", "organizations.members.read")],
)
async def test_organization_reads_require_permission(
    client, identity, db_session, suffix, permission_name
):
    user, _ = identity
    org = await create(client)
    organization = await db_session.get(Organization, org["id"])
    organization.owner_id = None
    await db_session.commit()
    path = f"/api/v1/organizations/{org['uuid']}{suffix}"
    response = await client.get(path)
    assert response.status_code == 403, response.text

    permission = await db_session.scalar(
        select(Permission).where(Permission.name == permission_name)
    )
    role = Role(name="organization-reader", organization_id=organization.id)
    db_session.add(role)
    await db_session.flush()
    db_session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
            UserRole(user_id=user.id, role_id=role.id, organization_id=organization.id),
        ]
    )
    await PermissionService.invalidate(db_session, organization.id)
    await db_session.commit()
    response = await client.get(path)
    assert response.status_code == 200, response.text


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
    role = Role(name="removed-role", organization_id=org["id"])
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
async def test_selection_requires_active_membership_and_preserves_context(
    client, identity, db_session
):
    user, session = identity
    selected = await create(client, "selected")
    target = await create(client, "target")
    outsider = Organization(name="Private", slug="private")
    db_session.add(outsider)
    await db_session.commit()
    response = await client.post(
        f"/api/v1/auth/organizations/{selected['uuid']}/select"
    )
    assert response.status_code == 200, response.text

    response = await client.post(f"/api/v1/auth/organizations/{outsider.uuid}/select")
    assert response.status_code == 404, response.text
    assert session.organization_id == selected["id"]

    membership = await db_session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == target["id"],
            OrganizationMembership.user_id == user.id,
        )
    )
    membership.is_active = False
    await db_session.commit()
    # Even the owner cannot select with an inactive membership.
    response = await client.post(f"/api/v1/auth/organizations/{target['uuid']}/select")
    assert response.status_code == 404, response.text
    assert session.organization_id == selected["id"]

    membership.is_active = True
    await db_session.commit()
    response = await client.post(f"/api/v1/auth/organizations/{target['uuid']}/select")
    assert response.status_code == 200, response.text
    assert session.organization_id == target["id"]


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
