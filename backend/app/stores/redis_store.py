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

    async def set_value(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is None:
            await self._redis.set(key, value)
            return
        await self._redis.set(key, value, ex=ttl_seconds)

    async def get_value(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def push_left(self, key: str, value: str) -> None:
        await self._redis.lpush(key, value)

    async def push_right(self, key: str, value: str) -> None:
        await self._redis.rpush(key, value)

    async def blocking_pop_left(self, key: str, timeout_seconds: int) -> str | None:
        result = await self._redis.blpop(key, timeout=timeout_seconds)
        if result is None:
            return None
        _, value = result
        return value

    async def list_length(self, key: str) -> int:
        return int(await self._redis.llen(key))

    async def list_range(self, key: str, start: int, end: int) -> list[str]:
        return list(await self._redis.lrange(key, start, end))

    async def sorted_add(self, key: str, member: str, score: float) -> None:
        await self._redis.zadd(key, {member: score})

    async def sorted_range_by_score(
        self,
        key: str,
        *,
        minimum: float,
        maximum: float,
        count: int,
    ) -> list[str]:
        return list(await self._redis.zrangebyscore(key, min=minimum, max=maximum, start=0, num=count))

    async def sorted_remove(self, key: str, member: str) -> int:
        return int(await self._redis.zrem(key, member))

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def increment_with_window(self, key: str, window_seconds: int) -> int:
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, window_seconds)
        return int(count)

    async def ttl(self, key: str) -> int:
        return int(await self._redis.ttl(key))

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self._redis.expire(key, ttl_seconds)
