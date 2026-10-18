from typing import Self

from app.services.mail import MailService
from app.types import AsyncService, JSONValue
from app.workers.base import BaseWorker


class EmailSendWorker(BaseWorker):
    """
    Background worker for sending emails asynchronously.

    Supports both plain text emails and template-based emails via
    integration with the MailService.
    """
    name = "email.send"

    async def _run(self: Self, *args, **kwargs) -> None:
        """
        Execute the email sending logic based on the provided arguments.

        If 'template' is present in kwargs, uses send_template,
        otherwise uses the standard send method.
        """
        service: AsyncService = (
            MailService.send_template if "template" in kwargs else MailService.send
        )

        await service(*args, **kwargs)

    @classmethod
    async def send(
        cls: type[EmailSendWorker],
        *,
        to: str,
        subject: str,
        text: str | None = None,
        html: str | None = None,
    ):
        """
        Enqueues a plain text or HTML email for asynchronous sending.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            text: Optional plain text body.
            html: Optional HTML body.
        """
        cls().delay(to=to, subject=subject, text=text, html=html)

    @classmethod
    async def send_template(
        cls: type[EmailSendWorker],
        *,
        to: str,
        subject: str,
        template: str,
        **context: JSONValue,
    ) -> None:
        """
        Enqueues a template-based email for asynchronous sending.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            template: Name of the email template to use.
            **context: Context variables for template rendering.
        """
        cls().delay(to=to, subject=subject, template=template, **context)
