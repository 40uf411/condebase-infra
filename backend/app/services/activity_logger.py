import logging
from typing import Any

from fastapi import Request

from ..core.security import request_client_ip
from ..stores.activity_store import ActivityStore

logger = logging.getLogger(__name__)


class ActivityLogger:
    def __init__(self, activity_store: ActivityStore) -> None:
        self._activity_store = activity_store

    async def log_event(
        self,
        *,
        request: Request,
        event_type: str,
        event_category: str,
        status_code: int | None = None,
        session: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            actor_sub = None
            if isinstance(session, dict):
                raw_sub = session.get("sub")
                if isinstance(raw_sub, str) and raw_sub.strip():
                    actor_sub = raw_sub.strip()

            await self._activity_store.append(
                event_type=event_type,
                event_category=event_category,
                actor_sub=actor_sub,
                session_id=getattr(request.state, "session_id", None),
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                ip_address=request_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                request_id=getattr(request.state, "request_id", None),
                metadata=metadata or {},
            )
        except Exception:
            logger.exception(
                "Activity log write failed for event_type=%s path=%s",
                event_type,
                request.url.path,
            )
