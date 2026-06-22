from typing import Optional

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables validation using Pydantic V2."""

    PROJECT_NAME: str = "Industrial Lathe Tools API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CORS_ORIGINS: str = "*"

    NOTION_TOKEN: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None

    INITIAL_SUPER_ADMIN_PHONE: Optional[str] = None
    INITIAL_SUPER_ADMIN_PASSWORD: Optional[str] = None
    INITIAL_SUPER_ADMIN_NAME: Optional[str] = "Super Admin"

    @field_validator("POSTGRES_PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long and not empty")
        if v == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed from default placeholder")
        return v

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field
    @property
    def redis_enabled(self) -> bool:
        return bool(self.REDIS_HOST)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
