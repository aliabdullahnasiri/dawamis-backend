from typing import Type

from cryptography.fernet import Fernet

from app.core.config import settings


class SecretEncryption:
    _fernet = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())

    @classmethod
    def encrypt(cls: Type[SecretEncryption], value: str) -> str:
        return cls._fernet.encrypt(value.encode()).decode()

    @classmethod
    def decrypt(cls: Type[SecretEncryption], value: str) -> str:
        return cls._fernet.decrypt(value.encode()).decode()
