from .auth import router as auth_router
from .health import router as health_router
from .profile import router as profile_router

__all__ = ["auth_router", "health_router", "profile_router"]
