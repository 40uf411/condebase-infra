import json
from typing import Any

from redis.asyncio import Redis


def login_state_key(state: str) -> str:
    return f"login_state:{state}"


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


class RedisStore:
    def __init__(self, url: str) -> None:
        self._redis: Redis = Redis.from_url(url, decode_responses=True)

    async def close(self) -> None:
        await self._redis.aclose()

    async def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(payload), ex=ttl_seconds)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self._redis.expire(key, ttl_seconds)
