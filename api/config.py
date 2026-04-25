from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/t2_schedule"
    JWT_SECRET_KEY: str = "CHANGE_ME_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    EXPORT_DIR: str = "/tmp"
    APP_ENV: str = "development"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.APP_ENV.lower() not in {"development", "dev", "test"}

    def validate_security(self) -> None:
        if self.is_production_like and (
            self.JWT_SECRET_KEY in {"CHANGE_ME_SECRET", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"}
            or len(self.JWT_SECRET_KEY) < 32
        ):
            raise ValueError("JWT_SECRET_KEY must be changed and be at least 32 characters long")
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origin is not allowed")


settings = Settings()
