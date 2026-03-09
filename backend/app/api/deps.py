from typing import Any

from fastapi import Depends, HTTPException, Request, status
from starlette.responses import Response

from ..core.authorization import ensure_permissions
from ..core.config import Settings, get_settings
from ..core.security import sign_session_cookie, verify_session_cookie
from ..services.activity_logger import ActivityLogger
from ..services.job_queue import JobQueue
from ..notifications import NotificationService
from ..services.sessions import get_session
from ..stores.redis_store import RedisStore
from ..stores.activity_store import ActivityStore
from ..stores.entity_store import EntityStore
from ..stores.user_store import AppUserStore


def get_redis_store(request: Request) -> RedisStore:
    return request.app.state.redis_store


def get_user_store(request: Request) -> AppUserStore:
    return request.app.state.user_store


def get_activity_store(request: Request) -> ActivityStore:
    return request.app.state.activity_store


def get_activity_logger(request: Request) -> ActivityLogger:
    return request.app.state.activity_logger


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.job_queue


def get_entity_store(request: Request) -> EntityStore:
    return request.app.state.entity_store


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


def _decode_session_cookie_value(raw_value: str | None, settings: Settings) -> str | None:
    if not raw_value:
        return None
    return verify_session_cookie(
        raw_value,
        signing_keys=settings.session_signing_keys,
    )


def set_auth_cookies(
    response: Response,
    *,
    settings: Settings,
    session_id: str,
    csrf_token: str,
) -> None:
    signed_session_id = sign_session_cookie(
        session_id=session_id,
        key_id=settings.session_signing_active_key_id,
        signing_key=settings.session_signing_keys[settings.session_signing_active_key_id],
    )
    response.set_cookie(
        key=settings.cookie_name,
        value=signed_session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
        max_age=settings.session_ttl_seconds,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
        max_age=settings.session_ttl_seconds,
    )


def clear_auth_cookies(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        domain=settings.cookie_domain,
        path="/",
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        domain=settings.cookie_domain,
        path="/",
    )


def _csrf_from_request(request: Request, settings: Settings) -> tuple[str | None, str | None]:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")
    return cookie_token, header_token


def require_csrf(request: Request, session: dict[str, Any]) -> None:
    settings = get_settings()
    cookie_token, header_token = _csrf_from_request(request, settings)
    session_token = session.get("csrf_token")
    if not cookie_token or not header_token or not session_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
    if not (cookie_token == header_token == session_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")


async def optional_session(request: Request) -> dict[str, Any] | None:
    cached_session = getattr(request.state, "auth_session", None)
    if cached_session is not None:
        return cached_session

    settings = get_settings()
    raw_session_cookie = request.cookies.get(settings.cookie_name)
    session_id = _decode_session_cookie_value(raw_session_cookie, settings)
    if raw_session_cookie and session_id is None:
        request.state.invalid_session_cookie = True
        return None
    if not session_id:
        return None

    request.state.session_id = session_id
    session = await get_session(
        redis_store=get_redis_store(request),
        session_id=session_id,
        ttl_seconds=settings.session_ttl_seconds,
    )
    request.state.auth_session = session
    return session


async def require_session(request: Request) -> dict[str, Any]:
    session = await optional_session(request)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return session


def require_permissions(*permissions: str):
    async def _dependency(session: dict[str, Any] = Depends(require_session)) -> dict[str, Any]:
        ensure_permissions(session, permissions)
        return session

    return _dependency
