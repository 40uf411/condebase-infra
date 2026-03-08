from typing import Any

from fastapi import HTTPException, Request, status
from starlette.responses import Response

from ..core.config import Settings, get_settings
from ..services.sessions import get_session
from ..stores.redis_store import RedisStore
from ..stores.user_store import AppUserStore


def get_redis_store(request: Request) -> RedisStore:
    return request.app.state.redis_store


def get_user_store(request: Request) -> AppUserStore:
    return request.app.state.user_store


def set_auth_cookies(
    response: Response,
    *,
    settings: Settings,
    session_id: str,
    csrf_token: str,
) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=session_id,
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
    settings = get_settings()
    session_id = request.cookies.get(settings.cookie_name)
    if not session_id:
        return None

    session = await get_session(
        redis_store=get_redis_store(request),
        session_id=session_id,
        ttl_seconds=settings.session_ttl_seconds,
    )
    return session


async def require_session(request: Request) -> dict[str, Any]:
    session = await optional_session(request)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return session
