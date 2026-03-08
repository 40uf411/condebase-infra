import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    keycloak_base_url: str = "https://auth.local"
    keycloak_internal_url: str = "http://keycloak:8080"
    keycloak_realm: str = "auth_app"
    keycloak_client_id: str = "auth-app-bff"
    keycloak_client_secret: str = ""
    keycloak_redirect_uri: str = "https://app.local/api/auth/callback"

    session_redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+psycopg://appuser:apppassword@host.docker.internal:5432/appdb"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    login_state_ttl_seconds: int = 900

    app_base_url: str = "https://app.local"
    api_base_url: str = "https://app.local/api"
    allowed_cors_origins: list[str] = Field(default_factory=lambda: ["https://app.local"])

    cookie_name: str = "app_session"
    csrf_cookie_name: str = "csrf_token"
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "none"
    cookie_domain: str | None = ".local"
    media_dir: str = "/app/uploads"
    max_avatar_mb: int = 5

    @field_validator(
        "keycloak_base_url",
        "keycloak_internal_url",
        "app_base_url",
        "api_base_url",
        mode="before",
    )
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def _empty_cookie_domain_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None

        # Single-label domains (for example: ".local" or "localhost") are
        # commonly rejected in Domain cookies by browsers. Use host-only
        # cookies instead in those cases.
        normalized = stripped[1:] if stripped.startswith(".") else stripped
        if "." not in normalized:
            return None

        return stripped

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def _normalize_allowed_cors_origins(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return ["https://app.local"]

        if isinstance(value, list):
            return value

        raw = value.strip()
        if not raw:
            return ["https://app.local"]

        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("ALLOWED_CORS_ORIGINS JSON value must be an array")
            return parsed

        return [item.strip() for item in raw.split(",") if item.strip()]

    @field_validator("allowed_cors_origins")
    @classmethod
    def _validate_allowed_cors_origins(cls, value: list[str]) -> list[str]:
        cleaned = [origin.rstrip("/") for origin in value if origin and origin.strip()]
        if not cleaned:
            raise ValueError("ALLOWED_CORS_ORIGINS must contain at least one origin")
        if "*" in cleaned:
            raise ValueError("ALLOWED_CORS_ORIGINS must not include '*' when credentials are enabled")
        return cleaned

    @field_validator("media_dir", mode="before")
    @classmethod
    def _normalize_media_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("MEDIA_DIR must not be empty")
        return cleaned

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("DATABASE_URL must not be empty")
        return cleaned

    @field_validator("max_avatar_mb")
    @classmethod
    def _validate_max_avatar_mb(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MAX_AVATAR_MB must be at least 1")
        if value > 20:
            raise ValueError("MAX_AVATAR_MB must be at most 20")
        return value

    @property
    def keycloak_public_realm_base(self) -> str:
        return f"{self.keycloak_base_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_internal_realm_base(self) -> str:
        return f"{self.keycloak_internal_url}/realms/{self.keycloak_realm}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
