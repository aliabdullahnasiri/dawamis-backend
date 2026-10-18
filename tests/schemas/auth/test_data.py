import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError
from app.core.exceptions.validation import (
    AuthTokensRequiredError,
    ChallengeTokenForbiddenError,
    ChallengeTokenRequiredError,
)
from app.schemas.auth.data import (
    LoginData,
    RefreshData,
    SessionData,
    TwoFactorSetupData,
    RecoveryCodesData,
)


def test_login_data_valid():
    data = {"access_token": "access", "refresh_token": "refresh"}
    model = LoginData(**data)
    assert model.access_token == data["access_token"]
    assert model.refresh_token == data["refresh_token"]

def test_login_data_missing_field():
    with pytest.raises(AuthTokensRequiredError):
        LoginData(access_token="access")


def test_refresh_data_valid():
    data = {"access_token": "access"}
    model = RefreshData(**data)
    assert model.access_token == data["access_token"]

def test_refresh_data_missing_field():
    with pytest.raises(ValidationError):
        RefreshData()

def test_session_data_valid():
    now = datetime.now()
    data = {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "ip_address": "127.0.0.1",
        "user_agent": "Mozilla/5.0",
        "last_used_at": now.isoformat(),
        "expires_at": now.isoformat(),
    }
    model = SessionData(**data)
    assert model.id == data["id"]
    assert model.uuid == UUID(data["uuid"])
    assert model.ip_address == data["ip_address"]
    assert model.user_agent == data["user_agent"]
    assert model.last_used_at == now
    assert model.expires_at == now

def test_session_data_invalid_uuid():
    with pytest.raises(ValidationError):
        SessionData(
            id=1,
            uuid="not-a-uuid",
            expires_at=datetime.now().isoformat(),
        )

def test_session_data_missing_required():
    with pytest.raises(ValidationError):
        SessionData(id=1, uuid="550e8400-e29b-41d4-a716-446655440000")

def test_two_factor_setup_data_valid():
    data = {
        "provisioning_uri": "otpauth://totp/Dawamis:user@example.com?secret=SECRET&issuer=Dawamis",
        "qr_code": "base64_qr_code",
    }
    model = TwoFactorSetupData(**data)
    assert model.provisioning_uri == data["provisioning_uri"]
    assert model.qr_code == data["qr_code"]

def test_two_factor_setup_data_missing_field():
    with pytest.raises(ValidationError):
        TwoFactorSetupData(provisioning_uri="uri")

def test_recovery_codes_data_valid():
    data = {"recovery_codes": ["code1", "code2", "code3"]}
    model = RecoveryCodesData(**data)
    assert model.recovery_codes == data["recovery_codes"]

def test_recovery_codes_data_invalid_type():
    with pytest.raises(ValidationError):
        RecoveryCodesData(recovery_codes="not-a-list")
