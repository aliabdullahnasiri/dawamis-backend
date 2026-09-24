from fastapi import Request

from app.core.config import settings


def _normalize_lang(lang: str) -> str:
    """Normalize language code to base language (e.g., 'en-US' -> 'en')."""
    normalized_lang = lang.strip().lower().replace("-", "_")
    return normalized_lang.split("_", 1)[0]

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
        base_lang = _normalize_lang(lang)

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
        base_lang = _normalize_lang(language)

        if base_lang in supported_languages:
            request.session["lang"] = base_lang
            return supported_languages[base_lang]

    # 4. Default
    return supported_languages.get(settings.DEFAULT_LANGUAGE, supported_languages.get("en", "en_US"))
