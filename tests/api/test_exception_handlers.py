import pytest
from fastapi import Depends
from sqlalchemy import select

from app.api.dependencies.db import DBSession
from app.core.exceptions import NotFoundError
from app.models import User


@pytest.mark.asyncio
@pytest.mark.parametrize("in_dependency", [False, True])
async def test_no_result_found_returns_404(app, client, in_dependency):
    """Actual ORM missing-row errors in routes and dependencies use the API envelope."""

    async def missing_user(db: DBSession):
        result = await db.execute(select(User).where(User.id == -1))
        return result.scalar_one()

    async def endpoint():
        return {"unexpected": True}

    path = "/test-no-result-found"
    app.add_api_route(
        path,
        endpoint if in_dependency else missing_user,
        dependencies=[Depends(missing_user)] if in_dependency else [],
    )
    try:
        response = await client.get(path)
        assert response.status_code == 404, response.text
        assert response.json() == {
            "type": "not_found",
            "message": "Resource not found.",
        }
    finally:
        app.router.routes[:] = [
            route for route in app.router.routes if getattr(route, "path", None) != path
        ]


@pytest.mark.asyncio
async def test_domain_not_found_retains_its_message(app, client):
    """The generic SQLAlchemy fallback preserves explicitly raised domain errors."""

    async def endpoint():
        raise NotFoundError(message="Organization not found.")

    path = "/test-domain-not-found"
    app.add_api_route(path, endpoint)
    try:
        response = await client.get(path)
        assert response.status_code == 404, response.text
        assert response.json() == {
            "type": "not_found",
            "message": "Organization not found.",
        }
    finally:
        app.router.routes[:] = [
            route for route in app.router.routes if getattr(route, "path", None) != path
        ]
