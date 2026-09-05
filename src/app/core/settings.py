from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "DawaMIS API"
    APP_DESCRIPTION: str = "Backend API for DawaMIS pharmacy management system."
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "your-secret-key"

    JWT_SECRET_KEY: str = "dev-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    SUPPORTED_LANGUAGES: dict[str, str] = {
        "en": "en_US",
        "fa": "fa_IR",
        "ps": "ps_AF",
    }

    DEFAULT_LANGUAGE: str = SUPPORTED_LANGUAGES["en"]

    DEFAULT_ROLES: tuple = ("ADMIN", "USER")

    LOCALES_DIR: Path = Path(__file__).resolve().parents[3] / "locales"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
