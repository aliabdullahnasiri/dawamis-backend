from typing import Self, Type

from app.services.mail import MailService
from app.types import AsyncService, JSONValue
from app.workers.base import BaseWorker


class EmailSendWorker(BaseWorker):
    name = "email.send"

    async def _run(self: Self, *args, **kwargs) -> None:
        service: AsyncService = (
            MailService.send_template if "template" in kwargs else MailService.send
        )

        await service(*args, **kwargs)

    @classmethod
    async def send(
        cls: Type[EmailSendWorker],
        *,
        to: str,
        subject: str,
        text: str | None = None,
        html: str | None = None,
    ):
        cls().delay(to=to, subject=subject, text=text, html=html)

    @classmethod
    async def send_template(
        cls: Type[EmailSendWorker],
        *,
        to: str,
        subject: str,
        template: str,
        **context: JSONValue,
    ) -> None:
        cls().delay(to=to, subject=subject, template=template, **context)
