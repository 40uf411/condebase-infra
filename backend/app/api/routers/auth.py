from datetime import datetime, timezone
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from starlette.responses import JSONResponse, RedirectResponse

from ...core.config import get_settings
from ..deps import (
    clear_auth_cookies,
    get_redis_store,
    get_user_store,
    optional_session,
    require_csrf,
    require_session,
    set_auth_cookies,
)
from ...core.security import challenge_from_verifier, generate_code_verifier, generate_state, safe_return_to
from ...domain.preferences import (
    default_web_preferences,
    extract_web_preferences,
    KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE,
    serialize_web_preferences,
)
from ...services.media import find_profile_picture_url
from ...services.serializers import user_profile_payload
from ...services.sessions import create_session, delete_session
from ...stores.redis_store import login_state_key

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _app_url(path: str, *, query: dict[str, str] | None = None) -> str:
    settings = get_settings()
    cleaned = safe_return_to(path, default="/")
    full = f"{settings.app_base_url}{cleaned}"
    if not query:
        return full
    return f"{full}?{urlencode(query)}"


async def _sync_app_user_record(request: Request, session_payload: dict) -> None:
    subject = session_payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        return

    await get_user_store(request).upsert_user(
        sub=subject,
        email=session_payload.get("email"),
        name=session_payload.get("name"),
        preferences=session_payload.get("preferences", {}),
    )


async def _start_login(
    request: Request,
    *,
    register: bool,
    return_to: str | None,
    prompt: str | None = None,
) -> RedirectResponse:
    settings = get_settings()
    redis_store = get_redis_store(request)

    state = generate_state()
    code_verifier = generate_code_verifier()
    code_challenge = challenge_from_verifier(code_verifier)
    safe_path = safe_return_to(return_to, default="/profile")

    await redis_store.set_json(
        login_state_key(state),
        {
            "code_verifier": code_verifier,
            "return_to": safe_path,
        },
        settings.login_state_ttl_seconds,
    )

    authorize_url = request.app.state.keycloak.build_authorize_url(
        state=state,
        code_challenge=code_challenge,
        register=register,
        prompt=prompt,
    )
    return RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)


@router.get("/login")
async def auth_login(
    request: Request,
    returnTo: str | None = Query(default=None),
    prompt: str | None = Query(default=None),
) -> RedirectResponse:
    return await _start_login(request, register=False, return_to=returnTo, prompt=prompt)


@router.get("/register")
async def auth_register(request: Request, returnTo: str | None = Query(default=None)) -> RedirectResponse:
    return await _start_login(request, register=True, return_to=returnTo)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    settings = get_settings()
    redis_store = get_redis_store(request)

    if error:
        query = {"error": error}
        if error_description:
            query["error_description"] = error_description
        return RedirectResponse(
            url=_app_url("/", query=query),
            status_code=status.HTTP_302_FOUND,
        )
    if not code or not state:
        return RedirectResponse(
            url=_app_url("/", query={"error": "missing_code_or_state"}),
            status_code=status.HTTP_302_FOUND,
        )

    state_key = login_state_key(state)
    login_state = await redis_store.get_json(state_key)
    await redis_store.delete(state_key)
    if login_state is None:
        logger.warning("OIDC callback rejected: invalid or expired state: %s", state)
        return RedirectResponse(
            url=_app_url("/", query={"error": "invalid_or_expired_state"}),
            status_code=status.HTTP_302_FOUND,
        )

    try:
        tokens = await request.app.state.keycloak.exchange_code_for_tokens(
            code=code,
            code_verifier=login_state["code_verifier"],
        )
        userinfo = await request.app.state.keycloak.fetch_userinfo(tokens["access_token"])
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Missing token fields from identity provider",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        response_text = exc.response.text.strip()
        logger.error(
            "Keycloak HTTP error during callback: status=%s body=%s",
            status_code,
            response_text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Identity provider exchange failed ({status_code})",
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Keycloak transport error during callback: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Identity provider exchange failed",
        ) from exc

    preferences = extract_web_preferences(userinfo)
    if preferences == default_web_preferences():
        try:
            account_profile = await request.app.state.keycloak.fetch_account_profile(tokens["access_token"])
            if isinstance(account_profile, dict):
                preferences = extract_web_preferences(account_profile.get("attributes"))
        except httpx.HTTPError:
            logger.warning(
                "Unable to fetch account profile attributes for subject %s; using default preferences",
                userinfo.get("sub"),
            )

    if isinstance(userinfo, dict):
        serialized_preferences = serialize_web_preferences(preferences)
        userinfo.setdefault(KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE, serialized_preferences)

    csrf_token = secrets.token_urlsafe(24)
    session_id = secrets.token_urlsafe(32)
    session_payload = {
        "userinfo": userinfo,
        "sub": userinfo.get("sub"),
        "email": userinfo.get("email"),
        "name": userinfo.get("name"),
        "given_name": userinfo.get("given_name"),
        "family_name": userinfo.get("family_name"),
        "preferred_username": userinfo.get("preferred_username"),
        "picture": userinfo.get("picture"),
        "email_verified": userinfo.get("email_verified", False),
        "access_token": tokens.get("access_token"),
        "id_token": tokens.get("id_token"),
        "token_response": tokens,
        "csrf_token": csrf_token,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "preferences": preferences,
    }

    local_picture = find_profile_picture_url(settings, userinfo.get("sub"))
    if local_picture is not None:
        session_payload["picture"] = local_picture
        if isinstance(session_payload["userinfo"], dict):
            session_payload["userinfo"]["picture"] = local_picture

    try:
        await _sync_app_user_record(request, session_payload)
    except Exception as exc:
        logger.exception("Failed to sync app_users record for subject %s", session_payload.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync user profile into app users table",
        ) from exc

    await create_session(
        redis_store=redis_store,
        session_id=session_id,
        payload=session_payload,
        ttl_seconds=settings.session_ttl_seconds,
    )

    redirect_to = _app_url(login_state.get("return_to", "/profile"))
    response = RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)
    set_auth_cookies(
        response,
        settings=settings,
        session_id=session_id,
        csrf_token=csrf_token,
    )
    return response


@router.get("/me")
async def auth_me(request: Request) -> dict:
    session = await optional_session(request)
    if session is None:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "user": user_profile_payload(session),
        "csrfToken": session.get("csrf_token"),
    }


@router.post("/logout")
async def auth_logout(request: Request) -> JSONResponse:
    settings = get_settings()
    session = await require_session(request)
    require_csrf(request, session)

    session_id = request.cookies.get(settings.cookie_name)
    if session_id:
        await delete_session(get_redis_store(request), session_id)

    logout_url = request.app.state.keycloak.build_logout_url(
        id_token_hint=session.get("id_token"),
        post_logout_redirect_uri=f"{settings.app_base_url}/",
    )
    response = JSONResponse({"ok": True, "logoutUrl": logout_url})
    clear_auth_cookies(response, settings=settings)
    return response
