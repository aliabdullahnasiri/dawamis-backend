from functools import lru_cache
from gettext import GNUTranslations, NullTranslations
from pathlib import Path
from typing import Union

from app.core.config import settings
from app.core.i18n.context import locale_context


@lru_cache
def get_translator(locale: str) -> Union[GNUTranslations, NullTranslations]:
    path = settings.LOCALES_DIR / locale / "LC_MESSAGES" / "messages.mo"

    if not path.exists():
        return NullTranslations()

    with path.open("rb") as file:
        return GNUTranslations(file)


def gettext(message: str) -> str:
    locale = locale_context.get()

    translator = get_translator(locale)

    return translator.gettext(message)
