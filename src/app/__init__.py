from typing import Self, Union

from fastapi import FastAPI

from app.api.middleware import register_middleware
from app.api.routers import health
from app.core.config import settings


class App:
    __object__: Union[App, None] = None

    def __new__(cls, *args, **kwargs) -> App:
        if cls.__object__ is not None:
            return cls.__object__

        cls.__object__ = super().__new__(cls)

        return cls.__object__

    def __init__(self: Self) -> None:
        self.app: FastAPI = self.create()

    def create(self) -> FastAPI:
        app = FastAPI(
            title=settings.APP_NAME,
            description=settings.APP_DESCRIPTION,
            version=settings.APP_VERSION,
        )

        App.register_routers(app)
        register_middleware(app)

        return app

    @staticmethod
    def register_routers(app: FastAPI) -> None:
        app.include_router(health.router, prefix="/api/v1")


def main() -> FastAPI:
    app: App = App()

    return app.app


if __name__ == "__main__":
    main()
