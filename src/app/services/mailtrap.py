from pathlib import Path
from typing import Any

import mailtrap as mt
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings


class MailtrapService:
    """Email delivery service using Mailtrap."""

    _template_dir = Path(__file__).resolve().parent.parent / "templates"

    _jinja = Environment(
        loader=FileSystemLoader(_template_dir),
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
        ),
    )

    @classmethod
    def render_template(
        cls,
        template: str,
        **context: Any,
    ) -> str:
        """
        Render an email template using Jinja2.

        Args:
            template: Template path relative to the templates directory.
            **context: Variables available inside the template.

        Returns:
            Rendered HTML string.
        """
        jinja_template = cls._jinja.get_template(template)

        return jinja_template.render(**context)

    @staticmethod
    def send(
        *,
        to: str,
        subject: str,
        text: str | None = None,
        html: str | None = None,
    ) -> Any:
        """
        Send an email through Mailtrap.

        Args:
            to: Recipient email address.
            subject: Email subject.
            text: Plain-text email body.
            html: HTML email body.

        Returns:
            Mailtrap API response.
        """
        if text is None and html is None:
            raise ValueError("Email must contain either text or html content.")

        mail = mt.Mail(
            sender=mt.Address(
                email=settings.MAIL_FROM_EMAIL,
                name=settings.MAIL_FROM_NAME,
            ),
            to=[
                mt.Address(
                    email=to,
                )
            ],
            subject=subject,
            text=text,
            html=html,
        )

        client = mt.MailtrapClient(
            token=settings.MAILTRAP_API_TOKEN,
        )

        return client.send(mail)

    @classmethod
    def send_template(
        cls,
        *,
        to: str,
        subject: str,
        template: str,
        text: str | None = None,
        **context: Any,
    ) -> Any:
        """
        Render a Jinja2 template and send it through Mailtrap.

        Args:
            to: Recipient email address.
            subject: Email subject.
            template: Jinja2 template path.
            text: Optional plain-text fallback.
            **context: Variables passed to the template.

        Returns:
            Mailtrap API response.
        """
        html = cls.render_template(
            template,
            **context,
        )

        return cls.send(
            to=to,
            subject=subject,
            text=text,
            html=html,
        )

    @classmethod
    def send_verification_email(
        cls,
        *,
        to: str,
        verification_url: str,
        user_name: str,
    ) -> Any:
        """
        Send an account verification email.
        """
        return cls.send_template(
            to=to,
            subject="Verify your Dawamis account",
            template="emails/verification.html",
            user_name=user_name,
            verification_url=verification_url,
        )

    @classmethod
    def send_password_reset_email(
        cls,
        *,
        to: str,
        reset_url: str,
        user_name: str,
    ) -> Any:
        """
        Send a password reset email.
        """
        return cls.send_template(
            to=to,
            subject="Reset your Dawamis password",
            template="emails/password_reset.html",
            user_name=user_name,
            reset_url=reset_url,
        )

    @classmethod
    def send_welcome_email(
        cls,
        *,
        to: str,
        user_name: str,
    ) -> Any:
        """
        Send a welcome email.
        """
        return cls.send_template(
            to=to,
            subject="Welcome to Dawamis",
            template="emails/welcome.html",
            user_name=user_name,
        )
