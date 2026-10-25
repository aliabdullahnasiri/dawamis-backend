from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient, fake_session: dict[str, Any]):
    """
    Test the health check endpoint.

    Verifies that the /api/v1/health/ endpoint returns a 200 OK status
    when the database and application are healthy.
    """
    response = await client.get("/api/v1/health/")

    assert response.status_code == 200
