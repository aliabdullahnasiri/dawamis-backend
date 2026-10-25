from datetime import datetime

from app.schemas.user.data import UserData
from app.schemas.user.response import CreateUserResponse, GetUserResponse


def test_get_user_response_valid():
    data = {
        "success": True,
        "message": "User retrieved",
        "data": UserData(
            uuid="550e8400-e29b-41d4-a716-446655440000",
            first_name="John",
            middle_name=None,
            last_name="Doe",
            user_name="johndoe",
            email="john@example.com",
            birthday=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    }
    model = GetUserResponse(**data)
    assert model.success is True
    assert model.data.user_name == "johndoe"

def test_create_user_response_valid():
    data = {
        "success": True,
        "message": "User created",
        "data": UserData(
            uuid="550e8400-e29b-41d4-a716-446655440000",
            first_name="John",
            middle_name=None,
            last_name="Doe",
            user_name="johndoe",
            email="john@example.com",
            birthday=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    }
    model = CreateUserResponse(**data)
    assert model.success is True
    assert model.data.user_name == "johndoe"
