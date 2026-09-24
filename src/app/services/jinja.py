from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.core.i18n.types import T


class JinjaService:
    """Service for loading and rendering Jinja2 templates."""

    _template_dir = Path(__file__).resolve().parent.parent / "templates"

    _jinja = Environment(
        loader=FileSystemLoader(_template_dir),
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
        ),
    )

    @classmethod
    def render(
        cls: type[JinjaService],
        template_name: str,
        **context,
    ) -> str:
        """Render a template with the provided context."""
        template = cls._jinja.get_template(template_name)

        return template.render(**context | {"T": T, "settings": settings})
