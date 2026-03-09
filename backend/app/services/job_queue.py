import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from ..core.config import Settings
from ..stores.redis_store import RedisStore


class JobQueue:
    def __init__(self, *, redis_store: RedisStore, settings: Settings) -> None:
        self._redis_store = redis_store
        self._settings = settings
        self._queue_name = settings.job_queue_name
        self._delayed_queue_name = settings.job_queue_delayed_name
        self._dead_letter_queue_name = settings.job_queue_dead_letter_name

    async def enqueue(
        self,
        *,
        job_type: str,
        payload: dict[str, Any],
        max_attempts: int | None = None,
        delay_seconds: int = 0,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        envelope = {
            "id": secrets.token_urlsafe(18),
            "type": job_type,
            "payload": payload,
            "attempt": 0,
            "max_attempts": max_attempts or self._settings.job_default_max_attempts,
            "created_at": now,
            "updated_at": now,
            "last_error": None,
        }
        await self._publish(envelope, delay_seconds=max(delay_seconds, 0))
        return envelope

    async def _publish(self, envelope: dict[str, Any], *, delay_seconds: int) -> None:
        serialized = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True)
        if delay_seconds <= 0:
            await self._redis_store.push_right(self._queue_name, serialized)
            return

        run_at = time.time() + delay_seconds
        await self._redis_store.sorted_add(self._delayed_queue_name, serialized, run_at)

    async def dequeue(self) -> dict[str, Any] | None:
        raw = await self._redis_store.blocking_pop_left(
            self._queue_name,
            timeout_seconds=self._settings.job_worker_poll_seconds,
        )
        if raw is None:
            return None
        return json.loads(raw)

    async def promote_due_jobs(self) -> int:
        now = time.time()
        raw_due_jobs = await self._redis_store.sorted_range_by_score(
            self._delayed_queue_name,
            minimum=0,
            maximum=now,
            count=self._settings.job_promote_batch_size,
        )

        promoted = 0
        for raw in raw_due_jobs:
            removed = await self._redis_store.sorted_remove(self._delayed_queue_name, raw)
            if removed <= 0:
                continue
            await self._redis_store.push_right(self._queue_name, raw)
            promoted += 1

        return promoted

    async def schedule_retry(self, envelope: dict[str, Any], *, error_message: str) -> dict[str, Any]:
        next_attempt = int(envelope.get("attempt", 0)) + 1
        envelope["attempt"] = next_attempt
        envelope["updated_at"] = datetime.now(timezone.utc).isoformat()
        envelope["last_error"] = error_message
        backoff_seconds = self._settings.job_retry_backoff_seconds * max(next_attempt, 1)
        await self._publish(envelope, delay_seconds=backoff_seconds)
        return envelope

    async def move_to_dead_letter(self, envelope: dict[str, Any], *, error_message: str) -> dict[str, Any]:
        envelope["updated_at"] = datetime.now(timezone.utc).isoformat()
        envelope["last_error"] = error_message
        serialized = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True)
        await self._redis_store.push_right(self._dead_letter_queue_name, serialized)
        return envelope

    async def metrics(self) -> dict[str, int]:
        return {
            "queued": await self._redis_store.list_length(self._queue_name),
            "deadLetter": await self._redis_store.list_length(self._dead_letter_queue_name),
        }
