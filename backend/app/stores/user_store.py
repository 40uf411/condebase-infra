import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..domain.preferences import normalize_web_preferences


class AppUserStore:
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

    async def upsert_user(
        self,
        *,
        sub: str,
        email: str | None,
        name: str | None,
        preferences: dict[str, Any],
    ) -> None:
        normalized_preferences = normalize_web_preferences(preferences)
        serialized_preferences = json.dumps(
            normalized_preferences,
            separators=(",", ":"),
            ensure_ascii=True,
        )

        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO app_users (
                        sub,
                        email,
                        name,
                        preferred_language,
                        theme,
                        web_preferences,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :sub,
                        :email,
                        :name,
                        :preferred_language,
                        :theme,
                        CAST(:web_preferences AS jsonb),
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (sub) DO UPDATE SET
                        email = EXCLUDED.email,
                        name = EXCLUDED.name,
                        preferred_language = EXCLUDED.preferred_language,
                        theme = EXCLUDED.theme,
                        web_preferences = EXCLUDED.web_preferences,
                        updated_at = NOW()
                    """
                ),
                {
                    "sub": sub,
                    "email": email,
                    "name": name,
                    "preferred_language": normalized_preferences["language"],
                    "theme": normalized_preferences["theme"],
                    "web_preferences": serialized_preferences,
                },
            )
