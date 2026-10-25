import pytest
from httpx import AsyncClient

from app.schemas.auth.request import (
    TOTPEnableRequest,
    TOTPVerifyRequest,
    TwoFactorDisableRequest,
)


@pytest.mark.asyncio
async def test_totp_setup(client: AsyncClient, fake_session):
    """Test TOTP setup endpoint."""
    res = await client.post("/api/v1/auth/2fa/totp/setup")
    assert res.status_code == 200
    assert "provisioning_uri" in res.json()["data"]
    assert "qr_code" in res.json()["data"]

@pytest.mark.asyncio
async def test_totp_enable(client: AsyncClient, fake_session):
    """Test TOTP enable endpoint (expecting failure due to invalid code)."""
    data = TOTPEnableRequest(code="123456")
    res = await client.post("/api/v1/auth/2fa/totp/enable", json=data.model_dump())
    assert res.status_code != 404

@pytest.mark.asyncio
async def test_totp_recovery_codes(client: AsyncClient, fake_session):
    """Test TOTP recovery codes regeneration."""
    data = TOTPVerifyRequest(code="123456")
    res = await client.post("/api/v1/auth/2fa/totp/recovery-codes", json=data.model_dump())
    assert res.status_code != 404

@pytest.mark.asyncio
async def test_totp_disable(client: AsyncClient, fake_session):
    """Test TOTP disable endpoint."""
    data = TwoFactorDisableRequest(password="password123", code="123456")
    res = await client.post("/api/v1/auth/2fa/totp/disable", json=data.model_dump())
    assert res.status_code != 404
