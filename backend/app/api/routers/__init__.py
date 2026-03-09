from .auth import router as auth_router
from .entities import router as entities_router
from .health import router as health_router
from .jobs import router as jobs_router
from .profile import router as profile_router

__all__ = ["auth_router", "entities_router", "health_router", "jobs_router", "profile_router"]
