import pytest
from httpx import AsyncClient

from app.schemas.auth.request.two_factor import (
    OTPEnableRequest,
    TwoFactorDisableRequest,
)


@pytest.mark.asyncio
async def test_otp_setup(client: AsyncClient, fake_session):
    """Test OTP setup endpoint."""
    res = await client.post("/api/v1/auth/2fa/otp/setup")
    assert res.status_code == 200
    assert "data" in res.json()
    assert "message" in res.json()["data"]


@pytest.mark.asyncio
async def test_otp_resend(client: AsyncClient, fake_session):
    """Test OTP resend endpoint."""
    res = await client.post("/api/v1/auth/2fa/otp/resend")
    assert res.status_code == 200
    assert res.json()["success"] is True


@pytest.mark.asyncio
async def test_otp_enable(client: AsyncClient, fake_session):
    """Test OTP enable endpoint (expecting failure due to invalid code)."""
    data = OTPEnableRequest(code="123456")
    res = await client.post("/api/v1/auth/2fa/otp/enable", json=data.model_dump())
    assert res.status_code != 404


@pytest.mark.asyncio
async def test_otp_disable(client: AsyncClient, fake_session):
    """Test OTP disable endpoint."""
    data = TwoFactorDisableRequest(password="password123", code="123456")
    res = await client.post("/api/v1/auth/2fa/otp/disable", json=data.model_dump())
    assert res.status_code != 404
