import pytest


@pytest.mark.asyncio
async def test_health(client, auth_headers):
    response = client.get("api/v1/health", headers=auth_headers)

    assert response.status_code == 200
