import base64
import hashlib
import hmac
import secrets
from typing import Mapping
from urllib.parse import urlsplit

from fastapi import Request


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


def sign_session_cookie(*, session_id: str, key_id: str, signing_key: str) -> str:
    message = f"{key_id}.{session_id}".encode("utf-8")
    digest = hmac.new(signing_key.encode("utf-8"), message, hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return f"{key_id}.{session_id}.{signature}"


def verify_session_cookie(
    signed_value: str,
    *,
    signing_keys: Mapping[str, str],
) -> str | None:
    if not signed_value:
        return None

    parts = signed_value.split(".")
    if len(parts) != 3:
        return None

    key_id, session_id, provided_signature = parts
    if not key_id or not session_id or not provided_signature:
        return None

    signing_key = signing_keys.get(key_id)
    if not isinstance(signing_key, str) or not signing_key:
        return None

    expected = sign_session_cookie(session_id=session_id, key_id=key_id, signing_key=signing_key)
    expected_signature = expected.rsplit(".", 1)[1]
    if not hmac.compare_digest(expected_signature, provided_signature):
        return None

    return session_id


def request_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"
