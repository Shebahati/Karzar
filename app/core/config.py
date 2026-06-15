# app/core/config.py

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and environment variables validation using Pydantic V2.
    """
    PROJECT_NAME: str = "Industrial Lathe Tools API"
    VERSION: str = "1.0.0"

    # PostgreSQL Database Credentials
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    # Redis Credentials
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        """
        Dynamically construct the asyncpg database URI.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Pydantic V2 config for environment variables
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Instantiate settings to be imported across the application
settings = Settings()