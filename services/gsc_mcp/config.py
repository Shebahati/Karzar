from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

GOOGLE_OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

ALLOWED_DIMENSIONS = frozenset(
    {"date", "query", "page", "country", "device", "searchAppearance"}
)
ALLOWED_SEARCH_TYPES = frozenset({"web", "image", "video", "news", "googleNews", "discover"})

DEFAULT_GSC_SITE_URL = "sc-domain:karzartools.com"
DEFAULT_ALLOWED_ORIGINS = (
    "https://www.karzartools.com",
    "https://karzartools.com",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gsc_site_url: str = Field(default=DEFAULT_GSC_SITE_URL, alias="GSC_SITE_URL")
    gsc_allowed_origins: str = Field(
        default=",".join(DEFAULT_ALLOWED_ORIGINS),
        alias="GSC_ALLOWED_ORIGINS",
    )
    gsc_allow_foreign_properties: bool = Field(default=False, alias="GSC_ALLOW_FOREIGN_PROPERTIES")

    google_gsc_client_id: str | None = Field(default=None, alias="GOOGLE_GSC_CLIENT_ID")
    google_gsc_client_secret: str | None = Field(default=None, alias="GOOGLE_GSC_CLIENT_SECRET")
    google_gsc_refresh_token: str | None = Field(default=None, alias="GOOGLE_GSC_REFRESH_TOKEN")

    crux_api_key: str | None = Field(default=None, alias="CRUX_API_KEY")

    karzar_mcp_access_token: str | None = Field(default=None, alias="KARZAR_MCP_ACCESS_TOKEN")

    gsc_http_timeout_seconds: float = Field(default=30.0, alias="GSC_HTTP_TIMEOUT_SECONDS")
    gsc_max_retries: int = Field(default=3, alias="GSC_MAX_RETRIES")
    gsc_max_row_limit: int = Field(default=25000, alias="GSC_MAX_ROW_LIMIT")
    gsc_max_date_span_days: int = Field(default=480, alias="GSC_MAX_DATE_SPAN_DAYS")
    gsc_max_response_bytes: int = Field(default=5_000_000, alias="GSC_MAX_RESPONSE_BYTES")

    gsc_inspection_max_per_request: int = Field(default=10, alias="GSC_INSPECTION_MAX_PER_REQUEST")
    gsc_inspection_daily_soft_limit: int = Field(default=100, alias="GSC_INSPECTION_DAILY_SOFT_LIMIT")

    mcp_host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    mcp_port: int = Field(default=8010, alias="MCP_PORT")
    mcp_public_base_url: str = Field(default="http://127.0.0.1:8010", alias="MCP_PUBLIC_BASE_URL")

    user_agent: str = Field(default="Karzar-GSC-MCP/0.1 (+https://www.karzartools.com)", alias="GSC_USER_AGENT")

    @field_validator("gsc_max_retries")
    @classmethod
    def _max_retries_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("GSC_MAX_RETRIES must be >= 0")
        return v

    @property
    def allowed_origins(self) -> tuple[str, ...]:
        parts = [p.strip() for p in self.gsc_allowed_origins.split(",") if p.strip()]
        return tuple(parts) if parts else DEFAULT_ALLOWED_ORIGINS

    @property
    def google_oauth_configured(self) -> bool:
        return bool(
            self.google_gsc_client_id
            and self.google_gsc_client_secret
            and self.google_gsc_refresh_token
        )

    @property
    def crux_configured(self) -> bool:
        return bool(self.crux_api_key)

    @property
    def mcp_auth_configured(self) -> bool:
        return bool(self.karzar_mcp_access_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
