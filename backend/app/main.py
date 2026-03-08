from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.router import api_router
from .core.config import get_settings
from .services.keycloak_oidc import KeycloakOIDC
from .services.media import ensure_media_directories
from .stores.redis_store import RedisStore
from .stores.user_store import AppUserStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis_store = RedisStore(settings.session_redis_url)
    http_client = httpx.AsyncClient(timeout=10.0)
    user_store = AppUserStore(settings.database_url)
    await user_store.initialize()

    app.state.redis_store = redis_store
    app.state.http_client = http_client
    app.state.keycloak = KeycloakOIDC(settings=settings, http_client=http_client)
    app.state.user_store = user_store

    try:
        yield
    finally:
        await http_client.aclose()
        await redis_store.close()
        await user_store.close()


settings = get_settings()
ensure_media_directories(settings)

app = FastAPI(
    title="Keycloak Auth Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/media", StaticFiles(directory=Path(settings.media_dir)), name="media")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "keycloak-auth-backend", "status": "ok"}
