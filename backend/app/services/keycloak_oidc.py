import json
from urllib.parse import urlencode

import httpx

from ..core.config import Settings


class KeycloakOIDC:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.http = http_client

    def build_authorize_url(
        self,
        *,
        state: str,
        code_challenge: str,
        register: bool = False,
        prompt: str | None = None,
    ) -> str:
        params = {
            "response_type": "code",
            "client_id": self.settings.keycloak_client_id,
            "redirect_uri": self.settings.keycloak_redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }
        if register:
            params["kc_action"] = "register"
        if prompt:
            params["prompt"] = prompt

        query = urlencode(params)
        return f"{self.settings.keycloak_public_realm_base}/protocol/openid-connect/auth?{query}"

    async def exchange_code_for_tokens(self, code: str, code_verifier: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.keycloak_redirect_uri,
            "client_id": self.settings.keycloak_client_id,
            "code_verifier": code_verifier,
        }
        if self.settings.keycloak_client_secret:
            payload["client_secret"] = self.settings.keycloak_client_secret

        response = await self.http.post(
            f"{self.settings.keycloak_internal_realm_base}/protocol/openid-connect/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()

    async def refresh_tokens(self, refresh_token: str) -> dict:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.settings.keycloak_client_id,
        }
        if self.settings.keycloak_client_secret:
            payload["client_secret"] = self.settings.keycloak_client_secret

        response = await self.http.post(
            f"{self.settings.keycloak_internal_realm_base}/protocol/openid-connect/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()

    async def fetch_userinfo(self, access_token: str) -> dict:
        response = await self.http.get(
            f"{self.settings.keycloak_internal_realm_base}/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def fetch_account_profile(self, access_token: str) -> dict:
        response = await self.http.get(
            f"{self.settings.keycloak_internal_realm_base}/account",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()

    async def update_web_preferences(
        self,
        *,
        access_token: str,
        attribute_name: str,
        preferences: dict[str, str],
    ) -> None:
        try:
            account_profile = await self.fetch_account_profile(access_token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 405}:
                account_profile = {}
            else:
                raise

        raw_attributes = account_profile.get("attributes")
        attributes: dict[str, list[str]] = {}

        if isinstance(raw_attributes, dict):
            for key, value in raw_attributes.items():
                if not isinstance(key, str):
                    continue
                if isinstance(value, list):
                    attributes[key] = [str(item) for item in value if item is not None]
                elif value is not None:
                    attributes[key] = [str(value)]

        serialized_preferences = json.dumps(preferences, separators=(",", ":"), ensure_ascii=True)
        attributes[attribute_name] = [serialized_preferences]

        payload: dict[str, object] = {"attributes": attributes}
        for source, target in (
            ("username", "username"),
            ("email", "email"),
            ("firstName", "firstName"),
            ("lastName", "lastName"),
        ):
            value = account_profile.get(source)
            if isinstance(value, str):
                payload[target] = value

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        response = await self.http.put(
            f"{self.settings.keycloak_internal_realm_base}/account",
            headers=headers,
            json=payload,
        )
        if response.status_code in {404, 405}:
            response = await self.http.post(
                f"{self.settings.keycloak_internal_realm_base}/account",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()

    def build_logout_url(self, id_token_hint: str | None, post_logout_redirect_uri: str) -> str:
        params = {
            "client_id": self.settings.keycloak_client_id,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        return (
            f"{self.settings.keycloak_public_realm_base}/protocol/openid-connect/logout?"
            f"{urlencode(params)}"
        )
