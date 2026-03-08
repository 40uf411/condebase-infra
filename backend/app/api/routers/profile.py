import logging

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, field_validator, model_validator

from ...core.config import get_settings
from ..deps import get_redis_store, get_user_store, require_csrf, require_session
from ...domain.preferences import (
    extract_web_preferences,
    KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE,
    is_supported_language,
    normalize_language,
    normalize_web_preferences,
    serialize_web_preferences,
)
from ...services.media import save_profile_picture
from ...services.serializers import user_profile_payload
from ...services.sessions import create_session

router = APIRouter(tags=["profile"])
logger = logging.getLogger(__name__)


class PreferencesUpdateRequest(BaseModel):
    language: str | None = None
    theme: str | None = None

    @field_validator("language")
    @classmethod
    def _normalize_language_input(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("Language must not be empty")
        return normalized

    @field_validator("theme")
    @classmethod
    def _normalize_theme_input(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if normalized not in {"light", "dark"}:
            raise ValueError("Theme must be either 'light' or 'dark'")
        return normalized

    @model_validator(mode="after")
    def _validate_non_empty(self) -> "PreferencesUpdateRequest":
        if self.language is None and self.theme is None:
            raise ValueError("At least one preference field must be provided")
        return self


async def _persist_session(request: Request, session: dict) -> None:
    settings = get_settings()
    session_id = request.cookies.get(settings.cookie_name)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    await create_session(
        redis_store=get_redis_store(request),
        session_id=session_id,
        payload=session,
        ttl_seconds=settings.session_ttl_seconds,
    )


@router.get("/profile")
async def get_profile(request: Request) -> dict:
    session = await require_session(request)
    return {"user": user_profile_payload(session, include_tokens=True)}


@router.post("/profile/picture")
async def upload_profile_picture(
    request: Request,
    file: UploadFile = File(...),
) -> dict:
    settings = get_settings()
    session = await require_session(request)
    require_csrf(request, session)

    claims = session.get("userinfo")
    subject = session.get("sub")
    if not subject and isinstance(claims, dict):
        subject = claims.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated subject is missing; cannot upload profile picture",
        )

    picture_url = await save_profile_picture(
        settings=settings,
        subject=subject,
        uploaded_file=file,
    )

    session["picture"] = picture_url
    if isinstance(claims, dict):
        claims["picture"] = picture_url
    else:
        session["userinfo"] = {"picture": picture_url, "sub": subject}

    await _persist_session(request, session)

    return {"picture": picture_url, "user": user_profile_payload(session, include_tokens=True)}


@router.put("/profile/preferences")
async def update_profile_preferences(request: Request, payload: PreferencesUpdateRequest) -> dict:
    session = await require_session(request)
    require_csrf(request, session)

    access_token = session.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token is missing from session",
        )

    current_preferences = (
        normalize_web_preferences(session.get("preferences"))
        if session.get("preferences") is not None
        else extract_web_preferences(session.get("userinfo"))
    )
    next_preferences = {**current_preferences}

    if payload.language is not None:
        if not is_supported_language(payload.language):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported language. Supported values: en, es, fr",
            )
        next_preferences["language"] = normalize_language(payload.language)

    if payload.theme is not None:
        next_preferences["theme"] = payload.theme

    if next_preferences == current_preferences:
        return {"preferences": next_preferences, "user": user_profile_payload(session, include_tokens=True)}

    try:
        await request.app.state.keycloak.update_web_preferences(
            access_token=access_token,
            attribute_name=KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE,
            preferences=next_preferences,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 401:
            logger.error(
                "Failed to update Keycloak web preferences for subject %s (status=%s): %s",
                session.get("sub"),
                exc.response.status_code,
                exc.response.text.strip(),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update preferences in Keycloak",
            ) from exc

        token_response = session.get("token_response")
        refresh_token = token_response.get("refresh_token") if isinstance(token_response, dict) else None
        if not isinstance(refresh_token, str) or not refresh_token.strip():
            logger.warning(
                "Cannot refresh Keycloak token while updating preferences for %s: refresh token missing",
                session.get("sub"),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identity provider session expired. Please sign in again.",
            ) from exc

        try:
            refreshed_tokens = await request.app.state.keycloak.refresh_tokens(refresh_token)
            refreshed_access_token = refreshed_tokens.get("access_token")
            if not isinstance(refreshed_access_token, str) or not refreshed_access_token.strip():
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to refresh identity provider session",
                )

            session["access_token"] = refreshed_access_token
            if isinstance(session.get("token_response"), dict):
                session["token_response"].update(refreshed_tokens)
            else:
                session["token_response"] = dict(refreshed_tokens)
            if isinstance(refreshed_tokens.get("id_token"), str):
                session["id_token"] = refreshed_tokens["id_token"]

            await request.app.state.keycloak.update_web_preferences(
                access_token=refreshed_access_token,
                attribute_name=KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE,
                preferences=next_preferences,
            )
        except httpx.HTTPStatusError as refresh_exc:
            status_code = refresh_exc.response.status_code
            logger.error(
                "Failed to refresh/apply Keycloak preferences for %s (status=%s): %s",
                session.get("sub"),
                status_code,
                refresh_exc.response.text.strip(),
            )
            if status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Identity provider session expired. Please sign in again.",
                ) from refresh_exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update preferences in Keycloak",
            ) from refresh_exc
        except httpx.HTTPError as refresh_exc:
            logger.error(
                "Keycloak transport error while refreshing/updating preferences for %s: %s",
                session.get("sub"),
                str(refresh_exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update preferences in Keycloak",
            ) from refresh_exc
    except httpx.HTTPError as exc:
        logger.error("Keycloak transport error while updating preferences for %s: %s", session.get("sub"), str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update preferences in Keycloak",
        ) from exc

    claims = session.get("userinfo")
    serialized_preferences = serialize_web_preferences(next_preferences)
    if isinstance(claims, dict):
        claims[KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE] = serialized_preferences
    else:
        session["userinfo"] = {
            "sub": session.get("sub"),
            KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE: serialized_preferences,
        }

    session["preferences"] = next_preferences
    await _persist_session(request, session)

    subject = session.get("sub")
    if isinstance(subject, str) and subject.strip():
        await get_user_store(request).upsert_user(
            sub=subject,
            email=session.get("email"),
            name=session.get("name"),
            preferences=next_preferences,
        )

    return {"preferences": next_preferences, "user": user_profile_payload(session, include_tokens=True)}
