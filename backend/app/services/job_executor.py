import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from ..core.config import Settings
from ..notifications import NotificationService

logger = logging.getLogger(__name__)


class JobExecutor:
    def __init__(
        self,
        *,
        settings: Settings,
        http_client: httpx.AsyncClient,
        notification_service: NotificationService,
    ) -> None:
        self._settings = settings
        self._http_client = http_client
        self._notification_service = notification_service

    async def execute(self, envelope: dict[str, Any]) -> None:
        job_type = str(envelope.get("type", "")).strip()
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Job payload must be a JSON object")

        if job_type == "notifications.send_template_email":
            await self._execute_send_template_email(payload)
            return
        if job_type == "notifications.send_raw_email":
            await self._execute_send_raw_email(payload)
            return
        if job_type == "webhooks.deliver":
            await self._execute_webhook_delivery(payload)
            return
        if job_type == "images.process_profile_picture":
            await self._execute_image_processing(payload)
            return
        if job_type == "tasks.run":
            await self._execute_async_task(payload)
            return

        raise ValueError(f"Unsupported job type: {job_type}")

    async def _execute_send_template_email(self, payload: dict[str, Any]) -> None:
        to_email = str(payload.get("to_email", "")).strip()
        template_name = str(payload.get("template_name", "")).strip()
        if not to_email or not template_name:
            raise ValueError("Template email job requires to_email and template_name")

        context = payload.get("context")
        if not isinstance(context, dict):
            context = {}

        await self._notification_service.send_template_email(
            to_email=to_email,
            template_name=template_name,
            context=context,
            subject_override=payload.get("subject_override"),
            from_email=payload.get("from_email"),
        )

    async def _execute_send_raw_email(self, payload: dict[str, Any]) -> None:
        to_email = str(payload.get("to_email", "")).strip()
        subject = str(payload.get("subject", "")).strip()
        text_body = str(payload.get("text_body", "")).strip()
        if not to_email or not subject or not text_body:
            raise ValueError("Raw email job requires to_email, subject, and text_body")

        html_body = payload.get("html_body")
        await self._notification_service.send_raw_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=str(html_body) if isinstance(html_body, str) else None,
            from_email=payload.get("from_email"),
        )

    async def _execute_webhook_delivery(self, payload: dict[str, Any]) -> None:
        url = str(payload.get("url", "")).strip()
        if not url:
            raise ValueError("Webhook job requires url")

        method = str(payload.get("method", "POST")).upper()
        if method not in {"POST", "PUT", "PATCH", "DELETE", "GET"}:
            raise ValueError(f"Unsupported webhook method: {method}")

        timeout = payload.get("timeout_seconds", self._settings.webhook_default_timeout_seconds)
        try:
            timeout_seconds = int(timeout)
        except (TypeError, ValueError) as exc:
            raise ValueError("Webhook timeout_seconds must be an integer") from exc
        timeout_seconds = min(max(timeout_seconds, 1), self._settings.webhook_max_timeout_seconds)

        raw_headers = payload.get("headers")
        headers: dict[str, str] = {}
        if isinstance(raw_headers, dict):
            for key, value in raw_headers.items():
                headers[str(key)] = str(value)

        json_payload = payload.get("json")

        response = await self._http_client.request(
            method=method,
            url=url,
            headers=headers or None,
            json=json_payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()

    async def _execute_image_processing(self, payload: dict[str, Any]) -> None:
        raw_file_path = payload.get("file_path")
        if not isinstance(raw_file_path, str) or not raw_file_path.strip():
            raise ValueError("Image processing job requires file_path")

        file_path = Path(raw_file_path).resolve()
        media_root = Path(self._settings.media_dir).resolve()
        if media_root not in file_path.parents and file_path != media_root:
            raise ValueError("Image processing path is outside MEDIA_DIR")

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        subject = payload.get("subject")
        await asyncio.to_thread(self._write_image_metadata, file_path, str(subject) if subject else None)

    def _write_image_metadata(self, file_path: Path, subject: str | None) -> None:
        binary = file_path.read_bytes()
        digest = hashlib.sha256(binary).hexdigest()
        metadata = {
            "file": str(file_path.name),
            "bytes": len(binary),
            "sha256": digest,
            "subject": subject,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        metadata_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        metadata_path.write_text(
            json.dumps(metadata, separators=(",", ":"), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    async def _execute_async_task(self, payload: dict[str, Any]) -> None:
        task_name = str(payload.get("task_name", "")).strip().lower()
        task_payload = payload.get("payload")
        if not isinstance(task_payload, dict):
            task_payload = {}

        if task_name == "log_message":
            message = str(task_payload.get("message", "")).strip()
            if not message:
                raise ValueError("tasks.run log_message requires payload.message")
            logger.info("async task log_message: %s", message)
            return

        if task_name == "ping_url":
            url = str(task_payload.get("url", "")).strip()
            if not url:
                raise ValueError("tasks.run ping_url requires payload.url")
            response = await self._http_client.get(
                url,
                timeout=min(
                    self._settings.webhook_default_timeout_seconds,
                    self._settings.webhook_max_timeout_seconds,
                ),
            )
            response.raise_for_status()
            return

        if task_name == "sleep":
            sleep_seconds = int(task_payload.get("seconds", 1))
            sleep_seconds = max(1, min(sleep_seconds, 30))
            await asyncio.sleep(sleep_seconds)
            return

        raise ValueError(f"Unsupported async task: {task_name}")
