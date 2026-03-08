import base64
import hashlib
import secrets
from urllib.parse import urlsplit


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("utf-8").rstrip("=")


def challenge_from_verifier(verifier: str) -> str:
    challenge = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")


def safe_return_to(return_to: str | None, default: str = "/profile") -> str:
    if not return_to:
        return default

    value = return_to.strip()
    if not value:
        return default

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return default
    if not value.startswith("/") or value.startswith("//"):
        return default
    if "\r" in value or "\n" in value:
        return default

    return value
