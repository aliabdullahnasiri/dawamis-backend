from app.schemas.base import BaseRequestModel
from app.schemas.user import CreateUserRequest


class RegisterRequest(CreateUserRequest):
    """
    Schema for the user registration request.

    Extends CreateUserRequest by adding a requirement to accept
    the terms and conditions.
    """

    accept_terms: bool
