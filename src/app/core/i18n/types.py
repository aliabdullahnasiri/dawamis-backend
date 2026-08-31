from dataclasses import dataclass

from app.core.i18n.translator import gettext


class LazyStr(str):

    def __new__(cls, message: str):
        return gettext(super().__new__(cls, message))
