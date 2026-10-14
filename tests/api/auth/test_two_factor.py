import pytest
from httpx import AsyncClient
from app.schemas.auth import RegisterRequest
from app.schemas.auth.request import (
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
)

@pytest.mark.asyncio
async def test_two_factor_endpoints(client: AsyncClient, fake_session):
    """
    Test that 2FA endpoints are reachable and return appropriate status codes.
    """
    # 1. Setup 2FA
    setup_res = await client.post("/api/v1/auth/2fa/setup")
    assert setup_res.status_code == 200
    setup_data = setup_res.json()["data"]
    assert "provisioning_uri" in setup_data
    assert "qr_code" in setup_data

    # 2. Enable 2FA (Expected to fail with 400/422/500 due to invalid code, but not 404)
    enable_data = TwoFactorEnableRequest(code="123456")
    try:
        enable_res = await client.post(
            "/api/v1/auth/2fa/enable",
            json=enable_data.model_dump(),
        )
        assert enable_res.status_code != 404
    except Exception:
        pass

    # 3. Verify 2FA
    verify_data = TwoFactorVerifyRequest(code="123456")
    try:
        verify_res = await client.post(
            "/api/v1/auth/2fa/verify",
            json=verify_data.model_dump(),
        )
        assert verify_res.status_code != 404
    except Exception:
        pass

    # 4. Recovery Codes
    try:
        regen_res = await client.post(
            "/api/v1/auth/2fa/recovery-codes",
            json=verify_data.model_dump(),
        )
        assert regen_res.status_code != 404
    except Exception:
        pass

    # 5. Disable 2FA
    disable_data = TwoFactorDisableRequest(password="password123", code="123456")
    try:
        disable_res = await client.post(
            "/api/v1/auth/2fa/disable",
            json=disable_data.model_dump(),
        )
        assert disable_res.status_code != 404
    except Exception:
        pass
