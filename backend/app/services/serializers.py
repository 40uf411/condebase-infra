from typing import Any

from ..domain.preferences import extract_web_preferences, normalize_web_preferences


def user_profile_payload(session: dict[str, Any], *, include_tokens: bool = False) -> dict[str, Any]:
    raw_claims = session.get("userinfo")
    claims = raw_claims if isinstance(raw_claims, dict) else {}
    raw_preferences = session.get("preferences")
    preferences = (
        normalize_web_preferences(raw_preferences)
        if raw_preferences is not None
        else extract_web_preferences(claims)
    )

    def claim_value(key: str, fallback_key: str) -> Any:
        value = claims.get(key)
        if value is not None:
            return value
        return session.get(fallback_key)

    payload = {
        "sub": claim_value("sub", "sub"),
        "email": claim_value("email", "email"),
        "name": claim_value("name", "name"),
        "givenName": claim_value("given_name", "given_name"),
        "familyName": claim_value("family_name", "family_name"),
        "username": claim_value("preferred_username", "preferred_username"),
        "picture": claim_value("picture", "picture"),
        "emailVerified": claim_value("email_verified", "email_verified") or False,
        "preferences": preferences,
        "preferredLanguage": preferences["language"],
        "theme": preferences["theme"],
        "claims": claims,
        "sessionIssuedAt": session.get("issued_at"),
    }

    if include_tokens:
        payload["idToken"] = session.get("id_token")
        payload["accessToken"] = session.get("access_token")
        raw_token_response = session.get("token_response")
        payload["tokenResponse"] = raw_token_response if isinstance(raw_token_response, dict) else {}

    return payload
