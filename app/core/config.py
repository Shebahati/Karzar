"""Application settings loaded from environment variables via Pydantic Settings."""

from typing import Optional

from typing_extensions import Self

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration; fails fast on missing or weak secrets."""

    PROJECT_NAME: str = "Industrial Lathe Tools API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENABLE_API_DOCS: bool = False

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
    STEP_UP_TOKEN_EXPIRE_MINUTES: int = 5
    STEP_UP_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    STEP_UP_ATTEMPT_WINDOW_SECONDS: int = Field(default=300, ge=30, le=3600)
    AUTH_MAX_ATTEMPTS: int = Field(default=10, ge=1, le=100)
    AUTH_ATTEMPT_WINDOW_SECONDS: int = Field(default=300, ge=30, le=3600)
    OTP_EXPIRE_SECONDS: int = Field(default=120, ge=60, le=600)
    OTP_DEV_ECHO: bool = False
    OTP_MESSAGE_TEMPLATE: str = "کد ورود شما به کارزار: {code}"

    # SMS delivery: "console" (logs only) or "kavenegar" (real provider).
    SMS_PROVIDER: str = "console"
    SMS_KAVENEGAR_API_KEY: Optional[str] = None
    SMS_KAVENEGAR_SENDER: Optional[str] = None
    SMS_KAVENEGAR_OTP_TEMPLATE: Optional[str] = None
    SMS_TIMEOUT_SECONDS: float = Field(default=10.0, ge=1.0, le=60.0)

    # Payment provider: "mock" (local dev) or "zarinpal" (production gateway).
    PAYMENT_PROVIDER: str = "mock"
    # Callback URL registered with the gateway (storefront or backend callback endpoint).
    PAYMENT_CALLBACK_URL: Optional[str] = None
    PAYMENT_SUCCESS_REDIRECT_URL: str = "http://localhost:3000/checkout/success"
    PAYMENT_FAILURE_REDIRECT_URL: str = "http://localhost:3000/checkout/payment/failed"
    ZARINPAL_MERCHANT_ID: Optional[str] = None
    ZARINPAL_REQUEST_URL: str = "https://payment.zarinpal.com/pg/v4/payment/request.json"
    ZARINPAL_VERIFY_URL: str = "https://payment.zarinpal.com/pg/v4/payment/verify.json"
    PAYMENT_TIMEOUT_SECONDS: float = Field(default=12.0, ge=1.0, le=60.0)
    PENDING_PAYMENT_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    ORDER_EXPIRY_SWEEP_INTERVAL_SECONDS: int = Field(default=60, ge=10, le=600)
    ADMIN_STEP_UP_PIN: str = Field(
        ...,
        min_length=6,
        max_length=12,
        description="Admin PIN for destructive actions",
    )
    ALLOW_PUBLIC_REGISTER: bool = False
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    IDEMPOTENCY_TTL_HOURS: int = Field(default=24, ge=1, le=168)

    APP_ENV: str = "development"
    LOG_TO_FILE: bool = True
    LOG_FILE: str = "logs/app.log"
    ENABLE_METRICS: bool = False

    # Public endpoint throttles (per client IP)
    PUBLIC_THROTTLE_CONTACT_MAX: int = Field(default=5, ge=1, le=1000)
    PUBLIC_THROTTLE_CONTACT_WINDOW: int = Field(default=300, ge=30, le=3600)
    PUBLIC_THROTTLE_CHECKOUT_MAX: int = Field(default=10, ge=1, le=1000)
    PUBLIC_THROTTLE_CHECKOUT_WINDOW: int = Field(default=300, ge=30, le=3600)
    PUBLIC_THROTTLE_TRACKING_MAX: int = Field(default=30, ge=1, le=1000)
    PUBLIC_THROTTLE_TRACKING_WINDOW: int = Field(default=60, ge=10, le=3600)
    PUBLIC_THROTTLE_PLP_MAX: int = Field(default=120, ge=1, le=5000)
    PUBLIC_THROTTLE_PLP_WINDOW: int = Field(default=60, ge=10, le=3600)

    # Security middleware
    MAX_REQUEST_BODY_BYTES: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    TRUSTED_HOSTS: str = ""
    ENFORCE_HTTPS: bool = False

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

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
        weak_placeholders = {
            "your-secret-key-change-in-production",
            "change-me-to-a-random-secret-key-at-least-32-chars",
            "replace-with-a-random-secret-key-at-least-32-chars",
        }
        if v in weak_placeholders:
            raise ValueError("SECRET_KEY must be changed from default placeholder")
        return v

    @field_validator("SMS_PROVIDER")
    @classmethod
    def validate_sms_provider(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in {"console", "kavenegar"}:
            raise ValueError("SMS_PROVIDER must be either 'console' or 'kavenegar'")
        return normalized

    @field_validator("PAYMENT_PROVIDER")
    @classmethod
    def validate_payment_provider(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in {"mock", "zarinpal"}:
            raise ValueError("PAYMENT_PROVIDER must be either 'mock' or 'zarinpal'")
        return normalized

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        normalized = v.strip().lower()
        allowed = {"development", "staging", "production"}
        if normalized not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        """Reject weak security settings when running outside debug mode."""
        if not self.DEBUG:
            weak_pins = {
                "000000",
                "123456",
                "111111",
                "121212",
                "654321",
                "84729101",
                "change-me-admin-pin",
            }
            if self.ADMIN_STEP_UP_PIN in weak_pins:
                raise ValueError(
                    "ADMIN_STEP_UP_PIN must be changed from default/weak value when DEBUG=False"
                )
            if self.OTP_DEV_ECHO:
                raise ValueError("OTP_DEV_ECHO must be False when DEBUG=False")
            if self.CORS_ORIGINS.strip() == "*":
                raise ValueError("CORS_ORIGINS cannot be '*' when DEBUG=False")
            if not self.REDIS_HOST:
                raise ValueError(
                    "REDIS_HOST is required when DEBUG=False so rate limits are shared across workers"
                )
            if self.APP_ENV == "production" and self.PAYMENT_PROVIDER == "mock":
                raise ValueError("PAYMENT_PROVIDER=mock is not allowed when APP_ENV=production")
        return self

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def trusted_hosts_list(self) -> list[str]:
        if not self.TRUSTED_HOSTS.strip():
            return []
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

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
