from fastapi import Request

from app.core.config import settings


def get_locale(request: Request) -> str:
    """
    Resolve the user's locale.

    Priority:
        1. Explicit ?lang=<language>
        2. Session language
        3. Accept-Language header
        4. Default language
    """

    supported_languages = settings.SUPPORTED_LANGUAGES

    # 1. Explicit ?lang=fa
    lang = request.query_params.get("lang")

    if lang:
        lang = lang.strip().lower()

        if lang in supported_languages:
            request.session["lang"] = lang
            return supported_languages[lang]

        # Support values such as ?lang=fa-IR or ?lang=fa_AF.
        normalized_lang = lang.replace("-", "_")
        base_lang = normalized_lang.split("_", 1)[0]

        if base_lang in supported_languages:
            request.session["lang"] = base_lang
            return supported_languages[base_lang]

    # 2. Session
    lang = request.session.get("lang")

    if lang in supported_languages:
        return supported_languages[lang]

    # 3. Accept-Language header
    accept_language = request.headers.get("Accept-Language", "")

    for language in accept_language.split(","):
        language = language.split(";", 1)[0].strip().lower()

        normalized_lang = language.replace("-", "_")
        base_lang = normalized_lang.split("_", 1)[0]

        if base_lang in supported_languages:
            request.session["lang"] = base_lang
            return supported_languages[base_lang]

    # 4. Default
    return supported_languages[settings.DEFAULT_LANGUAGE]
