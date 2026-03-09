from pathlib import Path
from typing import Any

from ..core.config import Settings
from .providers import (
    EmailPayload,
    LogNotificationProvider,
    NotificationProvider,
    SesNotificationProvider,
    SmtpNotificationProvider,
)


class _SafeTemplateValues(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class NotificationService:
    def __init__(self, *, settings: Settings, provider: NotificationProvider) -> None:
        self._settings = settings
        self._provider = provider
        self._template_directory = self._resolve_template_directory(settings.notification_templates_dir)

    @classmethod
    def create(cls, settings: Settings) -> "NotificationService":
        provider: NotificationProvider
        if settings.notification_provider == "smtp":
            provider = SmtpNotificationProvider(settings)
        elif settings.notification_provider == "ses":
            provider = SesNotificationProvider(settings)
        else:
            provider = LogNotificationProvider()

        return cls(settings=settings, provider=provider)

    async def send_template_email(
        self,
        *,
        to_email: str,
        template_name: str,
        context: dict[str, Any] | None = None,
        subject_override: str | None = None,
        from_email: str | None = None,
    ) -> None:
        values = _SafeTemplateValues((context or {}).copy())
        subject = subject_override or self._render_template(f"{template_name}_subject.txt", values)
        body = self._render_template(f"{template_name}_body.txt", values)
        html_body = self._render_optional_template(f"{template_name}_body.html", values)

        await self._provider.send_email(
            EmailPayload(
                to_email=to_email,
                from_email=from_email or self._settings.notification_from_email,
                subject=subject,
                text_body=body,
                html_body=html_body,
            )
        )

    async def send_raw_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
        from_email: str | None = None,
    ) -> None:
        await self._provider.send_email(
            EmailPayload(
                to_email=to_email,
                from_email=from_email or self._settings.notification_from_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        )

    def _resolve_template_directory(self, configured_path: str) -> Path:
        path = Path(configured_path)
        if path.is_absolute():
            return path

        from_cwd = (Path.cwd() / path).resolve()
        if from_cwd.exists():
            return from_cwd

        bundled_templates = (Path(__file__).resolve().parent / "templates").resolve()
        if bundled_templates.exists():
            return bundled_templates

        return from_cwd

    def _render_template(self, template_filename: str, values: dict[str, Any]) -> str:
        template_path = self._template_directory / template_filename
        if not template_path.exists():
            raise FileNotFoundError(f"Notification template not found: {template_path}")
        template = template_path.read_text(encoding="utf-8")
        return template.format_map(values).strip()

    def _render_optional_template(self, template_filename: str, values: dict[str, Any]) -> str | None:
        template_path = self._template_directory / template_filename
        if not template_path.exists():
            return None
        template = template_path.read_text(encoding="utf-8")
        return template.format_map(values).strip()
