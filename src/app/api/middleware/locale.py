import langcodes
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.i18n.context import locale_context
from app.core.i18n.locale import get_locale


class LocaleMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        locale = get_locale(request)

        token = locale_context.set(locale)

        try:
            response = await call_next(request)

            response.headers["Content-Language"] = locale

            return response

        finally:
            locale_context.reset(token)
