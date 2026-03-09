import asyncio

from ...core.config import Settings
from .base import EmailPayload, NotificationProvider


class SesNotificationProvider(NotificationProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_email(self, payload: EmailPayload) -> None:
        await asyncio.to_thread(self._send_sync, payload)

    def _send_sync(self, payload: EmailPayload) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for NOTIFICATION_PROVIDER=ses") from exc

        client = boto3.client("ses", region_name=self._settings.ses_region_name)
        request: dict = {
            "Source": payload.from_email,
            "Destination": {"ToAddresses": [payload.to_email]},
            "Message": {
                "Subject": {"Data": payload.subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": payload.text_body, "Charset": "UTF-8"},
                },
            },
        }
        if payload.html_body:
            request["Message"]["Body"]["Html"] = {"Data": payload.html_body, "Charset": "UTF-8"}

        if self._settings.ses_configuration_set:
            request["ConfigurationSetName"] = self._settings.ses_configuration_set

        client.send_email(**request)
