from typing import Any

from ..stores.redis_store import RedisStore, session_key


async def create_session(
    redis_store: RedisStore,
    session_id: str,
    payload: dict[str, Any],
    ttl_seconds: int,
) -> None:
    await redis_store.set_json(session_key(session_id), payload, ttl_seconds)


async def get_session(
    redis_store: RedisStore,
    session_id: str,
    ttl_seconds: int,
) -> dict[str, Any] | None:
    key = session_key(session_id)
    session = await redis_store.get_json(key)
    if session is None:
        return None

    await redis_store.expire(key, ttl_seconds)
    return session


async def delete_session(redis_store: RedisStore, session_id: str) -> None:
    await redis_store.delete(session_key(session_id))
