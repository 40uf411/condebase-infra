from dataclasses import dataclass

from ..stores.redis_store import RedisStore


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    current: int
    remaining: int
    retry_after_seconds: int


def rate_limit_key(scope: str, identifier: str) -> str:
    return f"rate_limit:{scope}:{identifier}"


def bruteforce_counter_key(identifier: str) -> str:
    return f"bruteforce:counter:{identifier}"


def bruteforce_block_key(identifier: str) -> str:
    return f"bruteforce:block:{identifier}"


async def consume_rate_limit(
    redis_store: RedisStore,
    *,
    scope: str,
    identifier: str,
    limit: int,
    window_seconds: int,
) -> RateLimitResult:
    key = rate_limit_key(scope, identifier)
    current = await redis_store.increment_with_window(key, window_seconds)
    ttl_seconds = max(await redis_store.ttl(key), 0)
    allowed = current <= limit

    return RateLimitResult(
        allowed=allowed,
        limit=limit,
        current=current,
        remaining=max(limit - current, 0),
        retry_after_seconds=ttl_seconds if not allowed else 0,
    )


async def auth_bruteforce_block_ttl(redis_store: RedisStore, *, identifier: str) -> int:
    return max(await redis_store.ttl(bruteforce_block_key(identifier)), 0)


async def register_auth_failure(
    redis_store: RedisStore,
    *,
    identifier: str,
    attempt_limit: int,
    window_seconds: int,
    block_seconds: int,
) -> tuple[bool, int]:
    key = bruteforce_counter_key(identifier)
    attempts = await redis_store.increment_with_window(key, window_seconds)

    if attempts >= attempt_limit:
        await redis_store.set_value(bruteforce_block_key(identifier), "1", ttl_seconds=block_seconds)
        return True, block_seconds

    retry_after = max(await redis_store.ttl(key), 0)
    return False, retry_after


async def clear_auth_failures(redis_store: RedisStore, *, identifier: str) -> None:
    await redis_store.delete(bruteforce_counter_key(identifier))
    await redis_store.delete(bruteforce_block_key(identifier))
