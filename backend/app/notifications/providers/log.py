import logging

from .base import EmailPayload, NotificationProvider

logger = logging.getLogger(__name__)


class LogNotificationProvider(NotificationProvider):
    async def send_email(self, payload: EmailPayload) -> None:
        logger.info(
            "Notification email [provider=log] to=%s subject=%s from=%s body=%s",
            payload.to_email,
            payload.subject,
            payload.from_email,
            payload.text_body,
        )
