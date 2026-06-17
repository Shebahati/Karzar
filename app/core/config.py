from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and environment variables validation using Pydantic V2.
    """
    PROJECT_NAME: str = "Industrial Lathe Tools API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # PostgreSQL Database Credentials
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    # Redis Credentials
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    #Notion API
    NOTION_TOKEN: str
    NOTION_DATABASE_ID: str

    @field_validator("POSTGRES_PORT")
    @classmethod
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long and not empty")
        if v == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed from default placeholder")
        return v

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