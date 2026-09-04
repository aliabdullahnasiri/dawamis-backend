from typing import Self, Union

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.middleware import register_middleware
from app.api.routers import auth, health
from app.core.config import settings
from app.errors import AppError
from app.errors.handlers import app_error_handler, request_validation_error_handler


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

        app.add_exception_handler(
            RequestValidationError, request_validation_error_handler
        )

        app.add_exception_handler(
            AppError,
            app_error_handler,
        )

        register_middleware(app)

        return app

    @staticmethod
    def register_routers(app: FastAPI) -> None:
        app.include_router(health.router, prefix="/api/v1")
        app.include_router(auth.router, prefix="/api/v1")


def main() -> FastAPI:
    app: App = App()

    return app.app


if __name__ == "__main__":
    main()
