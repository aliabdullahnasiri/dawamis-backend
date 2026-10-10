from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient, fake_session: Dict[str, Any]):
    response = await client.get("/api/v1/health/")

    assert response.status_code == 200
