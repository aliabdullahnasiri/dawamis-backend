from typing import Any

from fastapi import APIRouter

from app.api.routes import AsyncValidationRoute


class Router(APIRouter):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("route_class", AsyncValidationRoute)
        super().__init__(**kwargs)
