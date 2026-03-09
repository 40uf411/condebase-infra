import json
from functools import lru_cache
from typing import Any, Literal

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
    entities_model_path: str = "app/generated/entities_model.json"

    app_base_url: str = "https://app.local"
    api_base_url: str = "https://app.local/api"
    allowed_cors_origins: list[str] = Field(default_factory=lambda: ["https://app.local"])

    cookie_name: str = "app_session"
    csrf_cookie_name: str = "csrf_token"
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "none"
    cookie_domain: str | None = ".local"
    session_signing_active_key_id: str = "v1"
    session_signing_keys: dict[str, str] = Field(default_factory=lambda: {"v1": "replace_me_with_32+_chars"})

    security_headers_enabled: bool = True
    global_rate_limit_enabled: bool = True
    global_rate_limit_requests: int = 240
    global_rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 30
    auth_rate_limit_window_seconds: int = 60
    login_bruteforce_attempt_limit: int = 8
    login_bruteforce_window_seconds: int = 600
    login_bruteforce_block_seconds: int = 900

    job_queue_name: str = "app_jobs"
    job_queue_delayed_name: str = "app_jobs_delayed"
    job_queue_dead_letter_name: str = "app_jobs_dead"
    job_worker_poll_seconds: int = 2
    job_retry_backoff_seconds: int = 10
    job_default_max_attempts: int = 4
    job_promote_batch_size: int = 50

    webhook_default_timeout_seconds: int = 10
    webhook_max_timeout_seconds: int = 60

    notification_provider: Literal["log", "smtp", "ses"] = "log"
    notification_from_email: str = "no-reply@app.local"
    notification_templates_dir: str = "app/notifications/templates"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False
    ses_region_name: str = "us-east-1"
    ses_configuration_set: str | None = None

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

    @field_validator("session_signing_active_key_id", mode="before")
    @classmethod
    def _normalize_session_signing_active_key_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("SESSION_SIGNING_ACTIVE_KEY_ID must not be empty")
        return normalized

    @field_validator("session_signing_keys", mode="before")
    @classmethod
    def _normalize_session_signing_keys(cls, value: dict[str, str] | str | None) -> dict[str, str]:
        if value is None:
            return {"v1": "replace_me_with_32+_chars"}

        if isinstance(value, dict):
            parsed: dict[str, str] = {}
            for key, secret in value.items():
                key_id = str(key).strip()
                signing_secret = str(secret).strip()
                if key_id and signing_secret:
                    parsed[key_id] = signing_secret
            if not parsed:
                raise ValueError("SESSION_SIGNING_KEYS must define at least one key")
            return parsed

        raw = value.strip()
        if not raw:
            raise ValueError("SESSION_SIGNING_KEYS must not be empty")

        if raw.startswith("{"):
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                raise ValueError("SESSION_SIGNING_KEYS JSON value must be an object")
            return cls._normalize_session_signing_keys(loaded)

        parsed: dict[str, str] = {}
        for pair in raw.split(","):
            candidate = pair.strip()
            if not candidate:
                continue
            key_id, separator, secret = candidate.partition(":")
            if not separator:
                raise ValueError("SESSION_SIGNING_KEYS must use 'kid:secret' pairs")
            kid = key_id.strip()
            signing_secret = secret.strip()
            if not kid or not signing_secret:
                raise ValueError("SESSION_SIGNING_KEYS contains an empty key id or secret")
            parsed[kid] = signing_secret

        if not parsed:
            raise ValueError("SESSION_SIGNING_KEYS must define at least one key")

        return parsed

    @field_validator("session_signing_keys")
    @classmethod
    def _validate_session_signing_keys(cls, value: dict[str, str], info: Any) -> dict[str, str]:
        for key_id, secret in value.items():
            if "." in key_id:
                raise ValueError("SESSION_SIGNING_KEYS key ids must not contain '.'")
            if len(secret) < 16:
                raise ValueError(
                    f"SESSION_SIGNING_KEYS entry '{key_id}' is too short; use at least 16 characters"
                )

        active_key_id = str(info.data.get("session_signing_active_key_id", "")).strip()
        if active_key_id and active_key_id not in value:
            raise ValueError(
                "SESSION_SIGNING_ACTIVE_KEY_ID must reference an existing key in SESSION_SIGNING_KEYS"
            )

        return value

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

    @field_validator("entities_model_path", mode="before")
    @classmethod
    def _normalize_entities_model_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("ENTITIES_MODEL_PATH must not be empty")
        return cleaned

    @field_validator("notification_templates_dir", mode="before")
    @classmethod
    def _normalize_notification_templates_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("NOTIFICATION_TEMPLATES_DIR must not be empty")
        return cleaned

    @field_validator("notification_from_email", mode="before")
    @classmethod
    def _normalize_notification_from_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("NOTIFICATION_FROM_EMAIL must not be empty")
        return cleaned

    @field_validator("smtp_username", "smtp_password", "ses_configuration_set", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator(
        "global_rate_limit_requests",
        "global_rate_limit_window_seconds",
        "auth_rate_limit_requests",
        "auth_rate_limit_window_seconds",
        "login_bruteforce_attempt_limit",
        "login_bruteforce_window_seconds",
        "login_bruteforce_block_seconds",
    )
    @classmethod
    def _validate_positive_security_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Security rate-limit values must be at least 1")
        return value

    @field_validator(
        "job_worker_poll_seconds",
        "job_retry_backoff_seconds",
        "job_default_max_attempts",
        "job_promote_batch_size",
        "webhook_default_timeout_seconds",
        "webhook_max_timeout_seconds",
    )
    @classmethod
    def _validate_positive_background_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Background job and webhook values must be at least 1")
        return value

    @field_validator("smtp_port")
    @classmethod
    def _validate_smtp_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535")
        return value

    @field_validator("webhook_max_timeout_seconds")
    @classmethod
    def _validate_webhook_max_timeout(cls, value: int, info: Any) -> int:
        default_timeout = int(info.data.get("webhook_default_timeout_seconds", 1))
        if value < default_timeout:
            raise ValueError("WEBHOOK_MAX_TIMEOUT_SECONDS must be >= WEBHOOK_DEFAULT_TIMEOUT_SECONDS")
        return value

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
