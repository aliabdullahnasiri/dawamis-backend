from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.user.data import UserData


def test_user_data_valid():
    now = datetime.now()
    data = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "John",
        "middle_name": "Quincy",
        "last_name": "Doe",
        "user_name": "johndoe",
        "email": "john@example.com",
        "birthday": None,
        "created_at": now,
        "updated_at": now,
    }
    model = UserData(**data)
    assert model.uuid == UUID(data["uuid"])
    assert model.user_name == data["user_name"]
    assert model.email == data["email"]

def test_user_data_missing_required():
    with pytest.raises(ValidationError):
        UserData(uuid="550e8400-e29b-41d4-a716-446655440000")

def test_user_data_invalid_email():
    with pytest.raises(ValidationError):
        UserData(
            uuid="550e8400-e29b-41d4-a716-446655440000",
            user_name="johndoe",
            email="not-an-email",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
