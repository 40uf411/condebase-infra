import asyncio
import logging

import httpx

from .core.config import get_settings
from .notifications import NotificationService
from .services.job_executor import JobExecutor
from .services.job_queue import JobQueue
from .stores.redis_store import RedisStore

logger = logging.getLogger("app.worker")


async def run_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    settings = get_settings()
    redis_store = RedisStore(settings.session_redis_url)
    http_client = httpx.AsyncClient(timeout=20.0)
    queue = JobQueue(redis_store=redis_store, settings=settings)
    notifications = NotificationService.create(settings)
    executor = JobExecutor(
        settings=settings,
        http_client=http_client,
        notification_service=notifications,
    )

    logger.info(
        "Job worker started. queue=%s delayed=%s dead_letter=%s provider=%s",
        settings.job_queue_name,
        settings.job_queue_delayed_name,
        settings.job_queue_dead_letter_name,
        settings.notification_provider,
    )

    try:
        while True:
            promoted = await queue.promote_due_jobs()
            if promoted:
                logger.debug("Promoted %s delayed jobs", promoted)

            envelope = await queue.dequeue()
            if envelope is None:
                continue

            job_id = envelope.get("id")
            job_type = envelope.get("type")
            attempt = int(envelope.get("attempt", 0))
            max_attempts = int(envelope.get("max_attempts", settings.job_default_max_attempts))

            try:
                await executor.execute(envelope)
                logger.info("Job completed id=%s type=%s attempt=%s", job_id, job_type, attempt + 1)
            except Exception as exc:
                error_message = f"{type(exc).__name__}: {exc}"
                if attempt + 1 < max_attempts:
                    await queue.schedule_retry(envelope, error_message=error_message)
                    logger.warning(
                        "Job failed and scheduled for retry id=%s type=%s attempt=%s/%s error=%s",
                        job_id,
                        job_type,
                        attempt + 1,
                        max_attempts,
                        error_message,
                    )
                    continue

                envelope["attempt"] = attempt + 1
                await queue.move_to_dead_letter(envelope, error_message=error_message)
                logger.error(
                    "Job moved to dead-letter queue id=%s type=%s attempts=%s error=%s",
                    job_id,
                    job_type,
                    attempt + 1,
                    error_message,
                )
    finally:
        await http_client.aclose()
        await redis_store.close()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
