import json
from typing import Any

DEFAULT_LANGUAGE = "en"
DEFAULT_THEME = "light"

SUPPORTED_LANGUAGES = {"en", "es", "fr"}
SUPPORTED_THEMES = {"light", "dark"}

# Canonical attribute requested by the project.
KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE = "web-prefrences"


def default_web_preferences() -> dict[str, str]:
    return {
        "language": DEFAULT_LANGUAGE,
        "theme": DEFAULT_THEME,
    }


def is_supported_language(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized in SUPPORTED_LANGUAGES:
        return True
    base = normalized.split("-", 1)[0]
    return base in SUPPORTED_LANGUAGES


def normalize_language(value: Any) -> str:
    if not isinstance(value, str):
        return DEFAULT_LANGUAGE

    normalized = value.strip().lower()
    if not normalized:
        return DEFAULT_LANGUAGE

    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    base = normalized.split("-", 1)[0]
    if base in SUPPORTED_LANGUAGES:
        return base

    return DEFAULT_LANGUAGE


def normalize_theme(value: Any) -> str:
    if not isinstance(value, str):
        return DEFAULT_THEME

    normalized = value.strip().lower()
    if normalized in SUPPORTED_THEMES:
        return normalized
    return DEFAULT_THEME


def normalize_web_preferences(value: Any) -> dict[str, str]:
    candidate = value

    if isinstance(candidate, list):
        candidate = candidate[0] if candidate else {}

    if isinstance(candidate, str):
        stripped = candidate.strip()
        if not stripped:
            candidate = {}
        else:
            try:
                candidate = json.loads(stripped)
            except json.JSONDecodeError:
                candidate = {}

    if not isinstance(candidate, dict):
        candidate = {}

    return {
        "language": normalize_language(candidate.get("language")),
        "theme": normalize_theme(candidate.get("theme")),
    }


def extract_web_preferences(claims: Any) -> dict[str, str]:
    if isinstance(claims, dict):
        if KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE in claims:
            return normalize_web_preferences(claims.get(KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE))

    return default_web_preferences()


def serialize_web_preferences(value: Any) -> str:
    normalized = normalize_web_preferences(value)
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
