import asyncio
import smtplib
from email.message import EmailMessage

from ...core.config import Settings
from .base import EmailPayload, NotificationProvider


class SmtpNotificationProvider(NotificationProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_email(self, payload: EmailPayload) -> None:
        await asyncio.to_thread(self._send_sync, payload)

    def _send_sync(self, payload: EmailPayload) -> None:
        message = EmailMessage()
        message["Subject"] = payload.subject
        message["From"] = payload.from_email
        message["To"] = payload.to_email
        message.set_content(payload.text_body)
        if payload.html_body:
            message.add_alternative(payload.html_body, subtype="html")

        if self._settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(self._settings.smtp_host, self._settings.smtp_port, timeout=20) as client:
                self._login_if_needed(client)
                client.send_message(message)
            return

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=20) as client:
            if self._settings.smtp_use_starttls:
                client.starttls()
            self._login_if_needed(client)
            client.send_message(message)

    def _login_if_needed(self, client: smtplib.SMTP) -> None:
        if self._settings.smtp_username and self._settings.smtp_password:
            client.login(self._settings.smtp_username, self._settings.smtp_password)
