from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from ...core.config import get_settings
from ..deps import get_activity_logger, get_job_queue, require_permissions

router = APIRouter(prefix="/jobs", tags=["jobs"])


class EnqueueTemplateEmailRequest(BaseModel):
    toEmail: str
    templateName: str = Field(default="generic")
    context: dict[str, Any] = Field(default_factory=dict)
    subjectOverride: str | None = None
    fromEmail: str | None = None
    delaySeconds: int = 0
    maxAttempts: int | None = None

    @field_validator("toEmail", "templateName", mode="before")
    @classmethod
    def _non_empty_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be empty")
        return cleaned


class EnqueueRawEmailRequest(BaseModel):
    toEmail: str
    subject: str
    textBody: str
    htmlBody: str | None = None
    fromEmail: str | None = None
    delaySeconds: int = 0
    maxAttempts: int | None = None

    @field_validator("toEmail", "subject", "textBody", mode="before")
    @classmethod
    def _non_empty_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be empty")
        return cleaned


class EnqueueWebhookRequest(BaseModel):
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    json: dict[str, Any] | list[Any] | None = None
    timeoutSeconds: int | None = None
    delaySeconds: int = 0
    maxAttempts: int | None = None

    @field_validator("url", mode="before")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("url must not be empty")
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        return cleaned


class EnqueueImageProcessingRequest(BaseModel):
    filePath: str
    subject: str | None = None
    delaySeconds: int = 0
    maxAttempts: int | None = None

    @field_validator("filePath", mode="before")
    @classmethod
    def _validate_file_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("filePath must not be empty")
        return cleaned


class EnqueueTaskRequest(BaseModel):
    taskName: str
    payload: dict[str, Any] = Field(default_factory=dict)
    delaySeconds: int = 0
    maxAttempts: int | None = None

    @field_validator("taskName", mode="before")
    @classmethod
    def _validate_task_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("taskName must not be empty")
        return cleaned


@router.post("/email/template")
async def enqueue_template_email(
    request: Request,
    payload: EnqueueTemplateEmailRequest,
    session: dict = Depends(require_permissions("jobs:enqueue", "notifications:send")),
) -> dict[str, Any]:
    job = await get_job_queue(request).enqueue(
        job_type="notifications.send_template_email",
        payload={
            "to_email": payload.toEmail,
            "template_name": payload.templateName,
            "context": payload.context,
            "subject_override": payload.subjectOverride,
            "from_email": payload.fromEmail,
        },
        max_attempts=payload.maxAttempts,
        delay_seconds=payload.delaySeconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.enqueued.notifications.send_template_email",
        event_category="jobs",
        status_code=status.HTTP_202_ACCEPTED,
        session=session,
        metadata={"job_id": job["id"], "template_name": payload.templateName},
    )
    return {"queued": True, "jobId": job["id"], "jobType": job["type"]}


@router.post("/email/raw")
async def enqueue_raw_email(
    request: Request,
    payload: EnqueueRawEmailRequest,
    session: dict = Depends(require_permissions("jobs:enqueue", "notifications:send")),
) -> dict[str, Any]:
    job = await get_job_queue(request).enqueue(
        job_type="notifications.send_raw_email",
        payload={
            "to_email": payload.toEmail,
            "subject": payload.subject,
            "text_body": payload.textBody,
            "html_body": payload.htmlBody,
            "from_email": payload.fromEmail,
        },
        max_attempts=payload.maxAttempts,
        delay_seconds=payload.delaySeconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.enqueued.notifications.send_raw_email",
        event_category="jobs",
        status_code=status.HTTP_202_ACCEPTED,
        session=session,
        metadata={"job_id": job["id"], "to_email": payload.toEmail},
    )
    return {"queued": True, "jobId": job["id"], "jobType": job["type"]}


@router.post("/webhook")
async def enqueue_webhook(
    request: Request,
    payload: EnqueueWebhookRequest,
    session: dict = Depends(require_permissions("jobs:enqueue")),
) -> dict[str, Any]:
    settings = get_settings()
    timeout_seconds = payload.timeoutSeconds or settings.webhook_default_timeout_seconds
    if timeout_seconds > settings.webhook_max_timeout_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested timeout exceeds WEBHOOK_MAX_TIMEOUT_SECONDS",
        )

    job = await get_job_queue(request).enqueue(
        job_type="webhooks.deliver",
        payload={
            "url": payload.url,
            "method": payload.method,
            "headers": payload.headers,
            "json": payload.json,
            "timeout_seconds": timeout_seconds,
        },
        max_attempts=payload.maxAttempts,
        delay_seconds=payload.delaySeconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.enqueued.webhooks.deliver",
        event_category="jobs",
        status_code=status.HTTP_202_ACCEPTED,
        session=session,
        metadata={"job_id": job["id"], "url": payload.url},
    )
    return {"queued": True, "jobId": job["id"], "jobType": job["type"]}


@router.post("/image-process")
async def enqueue_image_processing(
    request: Request,
    payload: EnqueueImageProcessingRequest,
    session: dict = Depends(require_permissions("jobs:enqueue")),
) -> dict[str, Any]:
    job = await get_job_queue(request).enqueue(
        job_type="images.process_profile_picture",
        payload={
            "file_path": payload.filePath,
            "subject": payload.subject,
        },
        max_attempts=payload.maxAttempts,
        delay_seconds=payload.delaySeconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.enqueued.images.process_profile_picture",
        event_category="jobs",
        status_code=status.HTTP_202_ACCEPTED,
        session=session,
        metadata={"job_id": job["id"], "file_path": payload.filePath},
    )
    return {"queued": True, "jobId": job["id"], "jobType": job["type"]}


@router.post("/task")
async def enqueue_task(
    request: Request,
    payload: EnqueueTaskRequest,
    session: dict = Depends(require_permissions("jobs:enqueue")),
) -> dict[str, Any]:
    job = await get_job_queue(request).enqueue(
        job_type="tasks.run",
        payload={
            "task_name": payload.taskName,
            "payload": payload.payload,
        },
        max_attempts=payload.maxAttempts,
        delay_seconds=payload.delaySeconds,
    )
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.enqueued.tasks.run",
        event_category="jobs",
        status_code=status.HTTP_202_ACCEPTED,
        session=session,
        metadata={"job_id": job["id"], "task_name": payload.taskName},
    )
    return {"queued": True, "jobId": job["id"], "jobType": job["type"]}


@router.get("/metrics")
async def job_metrics(
    request: Request,
    session: dict = Depends(require_permissions("jobs:read")),
) -> dict[str, Any]:
    metrics = await get_job_queue(request).metrics()
    await get_activity_logger(request).log_event(
        request=request,
        event_type="jobs.metrics.read",
        event_category="jobs",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata=metrics,
    )
    return metrics
