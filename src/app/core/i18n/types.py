from dataclasses import dataclass

from app.core.i18n.translator import gettext


class T(str):

    def __new__(cls, message: str):
        return gettext(super().__new__(cls, message))
