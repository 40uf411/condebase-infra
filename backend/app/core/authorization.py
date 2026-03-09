import base64
import json
from typing import Any

from fastapi import HTTPException, status

Permission = str

ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "user": {
        "auth:logout",
        "entities:delete",
        "entities:read",
        "entities:write",
        "profile:read",
        "profile:picture:write",
        "profile:preferences:write",
    },
    "admin": {
        "activity:read",
        "auth:logout",
        "entities:delete",
        "entities:read",
        "entities:write",
        "jobs:enqueue",
        "jobs:read",
        "notifications:send",
        "profile:read",
        "profile:picture:write",
        "profile:preferences:write",
    },
}

DEFAULT_ROLE = "user"


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}

    payload = parts[1]
    padded_payload = payload + ("=" * (-len(payload) % 4))
    try:
        decoded = base64.urlsafe_b64decode(padded_payload.encode("utf-8"))
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _roles_from_claims(claims: dict[str, Any], *, client_id: str | None = None) -> set[str]:
    roles: set[str] = set()

    raw_roles = claims.get("roles")
    if isinstance(raw_roles, list):
        roles.update(str(value).strip() for value in raw_roles if str(value).strip())

    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        realm_roles = realm_access.get("roles")
        if isinstance(realm_roles, list):
            roles.update(str(value).strip() for value in realm_roles if str(value).strip())

    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        for resource_name, raw_resource_data in resource_access.items():
            if not isinstance(raw_resource_data, dict):
                continue
            resource_roles = raw_resource_data.get("roles")
            if not isinstance(resource_roles, list):
                continue
            for role in resource_roles:
                role_name = str(role).strip()
                if not role_name:
                    continue
                roles.add(role_name)
                if client_id and resource_name == client_id:
                    roles.add(role_name)

    return {role for role in roles if role}


def extract_roles(
    *,
    userinfo: dict[str, Any] | None,
    access_token: str | None,
    client_id: str | None = None,
) -> list[str]:
    roles: set[str] = {DEFAULT_ROLE}
    if isinstance(userinfo, dict):
        roles.update(_roles_from_claims(userinfo, client_id=client_id))

    if isinstance(access_token, str) and access_token.strip():
        token_claims = _decode_jwt_payload(access_token)
        roles.update(_roles_from_claims(token_claims, client_id=client_id))

    return sorted(role for role in roles if role)


def permissions_for_roles(roles: list[str] | set[str]) -> list[str]:
    permissions: set[str] = set()
    for role in roles:
        role_name = str(role).strip()
        if not role_name:
            continue
        permissions.update(ROLE_PERMISSIONS.get(role_name, set()))

    if DEFAULT_ROLE not in roles:
        permissions.update(ROLE_PERMISSIONS.get(DEFAULT_ROLE, set()))

    return sorted(permissions)


def effective_permissions(session: dict[str, Any]) -> set[str]:
    current_permissions = session.get("permissions")
    if isinstance(current_permissions, list):
        return {str(value).strip() for value in current_permissions if str(value).strip()}

    current_roles = session.get("roles")
    if isinstance(current_roles, list):
        return set(permissions_for_roles(current_roles))

    derived_roles = extract_roles(
        userinfo=session.get("userinfo") if isinstance(session.get("userinfo"), dict) else {},
        access_token=session.get("access_token"),
        client_id=None,
    )
    return set(permissions_for_roles(derived_roles))


def ensure_permissions(session: dict[str, Any], required_permissions: list[str] | tuple[str, ...]) -> None:
    permission_set = effective_permissions(session)

    missing = [permission for permission in required_permissions if permission not in permission_set]
    if not missing:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Missing required permissions: {', '.join(sorted(missing))}",
    )
