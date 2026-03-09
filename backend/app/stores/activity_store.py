import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class ActivityStore:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
        )

    async def close(self) -> None:
        await self._engine.dispose()

    async def initialize(self) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(text("SELECT 1"))

    async def append(
        self,
        *,
        event_type: str,
        event_category: str,
        actor_sub: str | None,
        session_id: str | None,
        method: str | None,
        path: str | None,
        status_code: int | None,
        ip_address: str | None,
        user_agent: str | None,
        request_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = metadata if isinstance(metadata, dict) else {}
        serialized_metadata = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)

        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO activity_logs (
                        event_type,
                        event_category,
                        actor_sub,
                        session_id,
                        method,
                        path,
                        status_code,
                        ip_address,
                        user_agent,
                        request_id,
                        metadata
                    )
                    VALUES (
                        :event_type,
                        :event_category,
                        :actor_sub,
                        :session_id,
                        :method,
                        :path,
                        :status_code,
                        :ip_address,
                        :user_agent,
                        :request_id,
                        CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "event_type": event_type,
                    "event_category": event_category,
                    "actor_sub": actor_sub,
                    "session_id": session_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "request_id": request_id,
                    "metadata": serialized_metadata,
                },
            )
