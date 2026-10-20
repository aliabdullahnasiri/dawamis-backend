import pytest
from pydantic import ValidationError
from app.schemas.auth.request import (
    LoginRequest,
    RegisterRequest,
    VerifyEmailRequest,
    ResendVerificationEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    TOTPEnableRequest,
    TOTPVerifyRequest,
    TwoFactorDisableRequest,
)

def test_login_request_valid():
    data = {"email": "user@example.com", "password": "password123"}
    model = LoginRequest(**data)
    assert model.email == data["email"]
    assert model.password == data["password"]

def test_login_request_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="password123")

def test_login_request_password_too_long():
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="a" * 129)

def test_register_request_valid():
    # RegisterRequest inherits from CreateUserRequest
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "user_name": "johndoe",
        "email": "john@example.com",
        "password": "password123",
        "accept_terms": True,
    }
    model = RegisterRequest(**data)
    assert model.accept_terms is True

def test_register_request_missing_terms():
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "user_name": "johndoe",
        "email": "john@example.com",
        "password": "password123",
    }
    with pytest.raises(ValidationError):
        RegisterRequest(**data)

def test_verify_email_request_valid():
    model = VerifyEmailRequest(token="valid_token")
    assert model.token == "valid_token"

def test_verify_email_request_empty_token():
    with pytest.raises(ValidationError):
        VerifyEmailRequest(token="")

def test_resend_verification_email_request_valid():
    model = ResendVerificationEmailRequest(email="user@example.com")
    assert model.email == "user@example.com"

def test_forgot_password_request_valid():
    model = ForgotPasswordRequest(email="user@example.com")
    assert model.email == "user@example.com"

def test_reset_password_request_valid():
    model = ResetPasswordRequest(token="token123", new_password="password123")
    assert model.token == "token123"
    assert model.new_password == "password123"

def test_reset_password_request_password_too_short():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="token123", new_password="short")

def test_change_password_request_valid():
    model = ChangePasswordRequest(current_password="old_password", new_password="new_password123")
    assert model.current_password == "old_password"
    assert model.new_password == "new_password123"

def test_change_password_request_new_password_too_short():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="old", new_password="short")

def test_two_factor_enable_request_valid():
    model = TOTPEnableRequest(code="123456")
    assert model.code == "123456"

def test_two_factor_enable_request_invalid_code():
    # pattern=r"^\d{6}$"
    with pytest.raises(ValidationError):
        TOTPEnableRequest(code="12345") # too short

    with pytest.raises(ValidationError):
        TOTPEnableRequest(code="1234567") # too long

    with pytest.raises(ValidationError):
        TOTPEnableRequest(code="abcdef") # not digits

def test_two_factor_verify_request_valid():
    model = TOTPVerifyRequest(code="123456")
    assert model.code == "123456"

def test_two_factor_verify_request_too_short():
    with pytest.raises(ValidationError):
        TOTPVerifyRequest(code="12345")

def test_two_factor_disable_request_valid():
    model = TwoFactorDisableRequest(password="password123", code="123456")
    assert model.password == "password123"
    assert model.code == "123456"

def test_two_factor_disable_request_invalid_code():
    with pytest.raises(ValidationError):
        TwoFactorDisableRequest(password="password123", code="12345")
