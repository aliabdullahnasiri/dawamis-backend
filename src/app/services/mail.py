import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import settings
from app.core.i18n.types import T
from app.services.jinja import JinjaService


class MailService:
    """Email delivery service using SMTP."""

    @staticmethod
    async def send(
        *,
        to: str,
        subject: str,
        text: str | None = None,
        html: str | None = None,
    ) -> None:
        """
        Send an email through SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject.
            text: Plain-text email body.
            html: HTML email body.
        """
        if text is None and html is None:
            raise ValueError(T("errors:email_must_contain_text_or_html_content"))

        message = EmailMessage()

        message["From"] = f"{settings.MAIL_FROM_NAME} " f"<{settings.MAIL_FROM_EMAIL}>"
        message["To"] = to
        message["Subject"] = subject

        if text is not None:
            message.set_content(text)

        if html is not None:
            message.add_alternative(
                html,
                subtype="html",
            )

        from fastapi.concurrency import run_in_threadpool

        def sync_send(message):
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
            ) as smtp:

                if settings.SMTP_USE_TLS:
                    smtp.starttls()

                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    smtp.login(
                        settings.SMTP_USERNAME,
                        settings.SMTP_PASSWORD,
                    )

                smtp.send_message(message)

        await run_in_threadpool(sync_send, message)

    @classmethod
    async def send_template(
        cls,
        *,
        to: str,
        subject: str,
        template: str,
        text: str | None = None,
        **context: Any,
    ) -> None:
        """
        Render a Jinja2 template and send it through SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject.
            template: Jinja2 template path.
            text: Optional plain-text fallback.
            **context: Variables passed to the template.
        """
        html = JinjaService.render(
            template,
            **context,
        )

        await cls.send(
            to=to,
            subject=subject,
            text=text,
            html=html,
        )
