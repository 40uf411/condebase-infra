from contextlib import asynccontextmanager
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from .api.router import api_router
from .api.deps import optional_session
from .core.config import get_settings
from .core.errors import (
    error_response,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from .core.security import request_client_ip
from .notifications import NotificationService
from .services.activity_logger import ActivityLogger
from .services.job_queue import JobQueue
from .services.rate_limit import consume_rate_limit
from .services.keycloak_oidc import KeycloakOIDC
from .services.media import ensure_media_directories
from .stores.redis_store import RedisStore
from .stores.activity_store import ActivityStore
from .stores.entity_store import EntityStore
from .stores.user_store import AppUserStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis_store = RedisStore(settings.session_redis_url)
    http_client = httpx.AsyncClient(timeout=10.0)
    user_store = AppUserStore(settings.database_url)
    entity_store = EntityStore(database_url=settings.database_url, model_path=settings.entities_model_path)
    activity_store = ActivityStore(settings.database_url)
    notification_service = NotificationService.create(settings)
    job_queue = JobQueue(redis_store=redis_store, settings=settings)
    await user_store.initialize()
    await entity_store.initialize()
    await activity_store.initialize()

    app.state.redis_store = redis_store
    app.state.http_client = http_client
    app.state.keycloak = KeycloakOIDC(settings=settings, http_client=http_client)
    app.state.user_store = user_store
    app.state.entity_store = entity_store
    app.state.activity_store = activity_store
    app.state.activity_logger = ActivityLogger(activity_store)
    app.state.notification_service = notification_service
    app.state.job_queue = job_queue

    try:
        yield
    finally:
        await http_client.aclose()
        await redis_store.close()
        await user_store.close()
        await entity_store.close()
        await activity_store.close()


settings = get_settings()
ensure_media_directories(settings)

app = FastAPI(
    title="Keycloak Auth Backend",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _apply_security_headers(response) -> None:
    if not settings.security_headers_enabled:
        return

    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=()",
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")


@app.middleware("http")
async def security_and_activity_middleware(request, call_next):
    request.state.request_id = secrets.token_hex(12)

    session = None
    if settings.cookie_name in request.cookies:
        session = await optional_session(request)

    rate_limit_result = None
    path = request.url.path
    if settings.global_rate_limit_enabled and path not in {"/healthz"}:
        rate_limit_result = await consume_rate_limit(
            request.app.state.redis_store,
            scope="global",
            identifier=request_client_ip(request),
            limit=settings.global_rate_limit_requests,
            window_seconds=settings.global_rate_limit_window_seconds,
        )
        if not rate_limit_result.allowed:
            response = error_response(
                request,
                status_code=429,
                code="RATE_LIMITED",
                message="Too many requests",
                details={
                    "retryAfterSeconds": rate_limit_result.retry_after_seconds,
                    "limit": rate_limit_result.limit,
                    "current": rate_limit_result.current,
                },
                headers={
                    "Retry-After": str(rate_limit_result.retry_after_seconds),
                    "X-RateLimit-Limit": str(rate_limit_result.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
            response.headers["X-Request-ID"] = request.state.request_id
            _apply_security_headers(response)
            await request.app.state.activity_logger.log_event(
                request=request,
                event_type="security.global_rate_limited",
                event_category="security",
                status_code=429,
                session=session,
                metadata={
                    "limit": rate_limit_result.limit,
                    "current": rate_limit_result.current,
                    "retry_after_seconds": rate_limit_result.retry_after_seconds,
                },
            )
            return response

    response = await call_next(request)

    if getattr(request.state, "invalid_session_cookie", False):
        response.delete_cookie(
            key=settings.cookie_name,
            domain=settings.cookie_domain,
            path="/",
        )
        await request.app.state.activity_logger.log_event(
            request=request,
            event_type="security.invalid_session_cookie",
            event_category="security",
            status_code=response.status_code,
            metadata={},
        )

    response.headers["X-Request-ID"] = request.state.request_id
    if rate_limit_result is not None:
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.remaining)
    _apply_security_headers(response)

    await request.app.state.activity_logger.log_event(
        request=request,
        event_type="http.request",
        event_category="http",
        status_code=response.status_code,
        session=session,
        metadata={
            "query": str(request.url.query),
            "invalid_session_cookie": bool(getattr(request.state, "invalid_session_cookie", False)),
        },
    )

    return response


app.include_router(api_router)
app.mount("/media", StaticFiles(directory=Path(settings.media_dir)), name="media")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "keycloak-auth-backend", "status": "ok"}
