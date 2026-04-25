from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL connection, e.g. postgres://user:password@localhost:5432/t2_schedule
    DATABASE_URL: AnyUrl = "postgresql+psycopg2://postgres:postgres@localhost:5432/t2_schedule"

    # JWT settings
    JWT_SECRET_KEY: str = "CHANGE_ME_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    class Config:
        env_file = ".env"


settings = Settings()

