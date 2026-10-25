from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.user import CreateUserRequest, UpdateUserRequest


def test_create_user_request_valid():
    data = {
        "first_name": "John",
        "middle_name": "Quincy",
        "last_name": "Doe",
        "user_name": "johndoe",
        "email": "john@example.com",
        "birthday": date(1990, 1, 1),
        "password": "password123",
    }
    model = CreateUserRequest(**data)
    assert model.first_name == "John"
    assert model.email == "john@example.com"
    assert model.password == "password123"

def test_create_user_request_missing_required():
    with pytest.raises(ValidationError):
        CreateUserRequest(user_name="johndoe")

def test_create_user_request_password_too_short():
    data = {
        "user_name": "johndoe",
        "email": "john@example.com",
        "password": "short",
    }
    with pytest.raises(ValidationError):
        CreateUserRequest(**data)

def test_create_user_request_invalid_email():
    data = {
        "user_name": "johndoe",
        "email": "not-an-email",
        "password": "password123",
    }
    with pytest.raises(ValidationError):
        CreateUserRequest(**data)

def test_create_user_request_name_too_long():
    data = {
        "first_name": "a" * 51,
        "user_name": "johndoe",
        "email": "john@example.com",
        "password": "password123",
    }
    with pytest.raises(ValidationError):
        CreateUserRequest(**data)

def test_update_user_request_valid():
    data = {
        "user_name": "johndoe_updated",
        "email": "updated@example.com",
    }
    model = UpdateUserRequest(**data)
    assert model.user_name == "johndoe_updated"

def test_update_user_request_missing_required():
    with pytest.raises(ValidationError):
        UpdateUserRequest(first_name="John")
