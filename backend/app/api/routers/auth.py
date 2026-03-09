from datetime import datetime, timezone
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.responses import JSONResponse, RedirectResponse

from ...core.authorization import extract_roles, permissions_for_roles
from ...core.config import get_settings
from ..deps import (
    clear_auth_cookies,
    get_activity_logger,
    get_redis_store,
    get_user_store,
    optional_session,
    require_permissions,
    require_csrf,
    set_auth_cookies,
)
from ...core.security import (
    challenge_from_verifier,
    generate_code_verifier,
    generate_state,
    request_client_ip,
    safe_return_to,
)
from ...domain.preferences import (
    default_web_preferences,
    extract_web_preferences,
    KEYCLOAK_WEB_PREFERENCES_ATTRIBUTE,
    serialize_web_preferences,
)
from ...services.rate_limit import (
    auth_bruteforce_block_ttl,
    clear_auth_failures,
    consume_rate_limit,
    register_auth_failure,
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


def _auth_identifier(request: Request) -> str:
    return request_client_ip(request)


async def _record_auth_failure(request: Request, *, reason: str) -> tuple[bool, int]:
    settings = get_settings()
    blocked, retry_after = await register_auth_failure(
        get_redis_store(request),
        identifier=_auth_identifier(request),
        attempt_limit=settings.login_bruteforce_attempt_limit,
        window_seconds=settings.login_bruteforce_window_seconds,
        block_seconds=settings.login_bruteforce_block_seconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="security.auth_failure",
        event_category="security",
        status_code=status.HTTP_401_UNAUTHORIZED,
        metadata={
            "reason": reason,
            "blocked": blocked,
            "retry_after_seconds": retry_after,
        },
    )
    return blocked, retry_after


async def _consume_auth_rate_limit(request: Request, *, scope: str) -> tuple[bool, int]:
    settings = get_settings()
    result = await consume_rate_limit(
        get_redis_store(request),
        scope=f"auth:{scope}",
        identifier=_auth_identifier(request),
        limit=settings.auth_rate_limit_requests,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    if result.allowed:
        return True, 0

    await get_activity_logger(request).log_event(
        request=request,
        event_type="security.auth_rate_limited",
        event_category="security",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        metadata={
            "scope": scope,
            "retry_after_seconds": result.retry_after_seconds,
            "limit": result.limit,
            "current": result.current,
        },
    )
    return False, result.retry_after_seconds


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
    activity_logger = get_activity_logger(request)

    allowed, retry_after = await _consume_auth_rate_limit(request, scope="start")
    if not allowed:
        return RedirectResponse(
            url=_app_url("/", query={"error": "rate_limited", "retry_after": str(retry_after)}),
            status_code=status.HTTP_302_FOUND,
        )

    blocked_ttl = await auth_bruteforce_block_ttl(redis_store, identifier=_auth_identifier(request))
    if blocked_ttl > 0:
        await activity_logger.log_event(
            request=request,
            event_type="security.auth_bruteforce_block",
            event_category="security",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            metadata={"retry_after_seconds": blocked_ttl},
        )
        return RedirectResponse(
            url=_app_url("/", query={"error": "login_temporarily_blocked", "retry_after": str(blocked_ttl)}),
            status_code=status.HTTP_302_FOUND,
        )

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
    await activity_logger.log_event(
        request=request,
        event_type="auth.register_started" if register else "auth.login_started",
        event_category="auth",
        status_code=status.HTTP_302_FOUND,
        metadata={"return_to": safe_path},
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
    activity_logger = get_activity_logger(request)

    allowed, retry_after = await _consume_auth_rate_limit(request, scope="callback")
    if not allowed:
        return RedirectResponse(
            url=_app_url("/", query={"error": "rate_limited", "retry_after": str(retry_after)}),
            status_code=status.HTTP_302_FOUND,
        )

    if error:
        blocked, blocked_retry = await _record_auth_failure(request, reason=f"idp_error:{error}")
        query = {"error": error}
        if error_description:
            query["error_description"] = error_description
        if blocked:
            query["error"] = "login_temporarily_blocked"
            query["retry_after"] = str(blocked_retry)
        return RedirectResponse(
            url=_app_url("/", query=query),
            status_code=status.HTTP_302_FOUND,
        )
    if not code or not state:
        blocked, blocked_retry = await _record_auth_failure(request, reason="missing_code_or_state")
        query = {"error": "missing_code_or_state"}
        if blocked:
            query = {"error": "login_temporarily_blocked", "retry_after": str(blocked_retry)}
        return RedirectResponse(
            url=_app_url("/", query=query),
            status_code=status.HTTP_302_FOUND,
        )

    state_key = login_state_key(state)
    login_state = await redis_store.get_json(state_key)
    await redis_store.delete(state_key)
    if login_state is None:
        blocked, blocked_retry = await _record_auth_failure(request, reason="invalid_or_expired_state")
        logger.warning("OIDC callback rejected: invalid or expired state: %s", state)
        query = {"error": "invalid_or_expired_state"}
        if blocked:
            query = {"error": "login_temporarily_blocked", "retry_after": str(blocked_retry)}
        return RedirectResponse(
            url=_app_url("/", query=query),
            status_code=status.HTTP_302_FOUND,
        )

    try:
        tokens = await request.app.state.keycloak.exchange_code_for_tokens(
            code=code,
            code_verifier=login_state["code_verifier"],
        )
        userinfo = await request.app.state.keycloak.fetch_userinfo(tokens["access_token"])
    except KeyError as exc:
        await _record_auth_failure(request, reason="missing_token_fields")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Missing token fields from identity provider",
        ) from exc
    except httpx.HTTPStatusError as exc:
        await _record_auth_failure(request, reason=f"idp_http_status:{exc.response.status_code}")
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
        await _record_auth_failure(request, reason="idp_transport_error")
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

    roles = extract_roles(
        userinfo=userinfo if isinstance(userinfo, dict) else {},
        access_token=tokens.get("access_token"),
        client_id=settings.keycloak_client_id,
    )
    permissions = permissions_for_roles(roles)

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
        "roles": roles,
        "permissions": permissions,
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

    await clear_auth_failures(redis_store, identifier=_auth_identifier(request))
    await activity_logger.log_event(
        request=request,
        event_type="auth.login_success",
        event_category="auth",
        status_code=status.HTTP_302_FOUND,
        session=session_payload,
        metadata={
            "return_to": login_state.get("return_to", "/profile"),
            "roles": roles,
        },
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
async def auth_logout(
    request: Request,
    session: dict = Depends(require_permissions("auth:logout")),
) -> JSONResponse:
    settings = get_settings()
    require_csrf(request, session)

    session_id = getattr(request.state, "session_id", None)
    if session_id:
        await delete_session(get_redis_store(request), session_id)

    logout_url = request.app.state.keycloak.build_logout_url(
        id_token_hint=session.get("id_token"),
        post_logout_redirect_uri=f"{settings.app_base_url}/",
    )
    response = JSONResponse({"ok": True, "logoutUrl": logout_url})
    clear_auth_cookies(response, settings=settings)
    await get_activity_logger(request).log_event(
        request=request,
        event_type="auth.logout",
        event_category="auth",
        status_code=status.HTTP_200_OK,
        session=session,
    )
    return response
