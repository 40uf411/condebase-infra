from fastapi import APIRouter

from .routers.auth import router as auth_router
from .routers.health import router as health_router
from .routers.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(profile_router)
