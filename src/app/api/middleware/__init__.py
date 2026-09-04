from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.middleware.database import DatabaseMiddleware
from app.api.middleware.locale import LocaleMiddleware
from app.core.config import settings


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LocaleMiddleware)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
    )

    app.add_middleware(DatabaseMiddleware)
