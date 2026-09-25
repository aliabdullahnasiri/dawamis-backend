from urllib.parse import urlencode

from app.core.config import settings


class URLService:
    @staticmethod
    def email_verification(token: str) -> str:
        query = urlencode({"token": token})

        return f"{settings.FRONTEND_URL}/verify-email?{query}"

    @staticmethod
    def password_reset(token: str) -> str:
        query = urlencode({"token": token})

        return f"{settings.FRONTEND_URL}/reset-password?{query}"

