from fastapi import Request

from app.core.config import settings


def get_locale(request: Request) -> str:
    # 1. Explicit ?lang=fa
    lang = request.query_params.get("lang")

    if lang in settings.SUPPORTED_LANGUAGES:
        request.session["lang"] = lang
        return lang

    # 2. Session
    lang = request.session.get("lang")

    if lang in settings.SUPPORTED_LANGUAGES:
        return lang

    # 3. Default
    return settings.DEFAULT_LANGUAGE
