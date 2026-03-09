from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailPayload:
    to_email: str
    from_email: str
    subject: str
    text_body: str
    html_body: str | None = None


class NotificationProvider(ABC):
    @abstractmethod
    async def send_email(self, payload: EmailPayload) -> None:
        raise NotImplementedError
