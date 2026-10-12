from typing import Type

from cryptography.fernet import Fernet

from app.core.config import settings


class SecretEncryption:
    """
    Utility class for symmetric encryption and decryption of sensitive values.

    Uses Fernet (AES-128 in CBC mode with HMAC-SHA256) to ensure that
    encrypted data cannot be read or modified without the key.
    """
    _fernet = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())

    @classmethod
    def encrypt(cls: Type[SecretEncryption], value: str) -> str:
        """
        Encrypt a plain text string.

        Args:
            value: The string to encrypt.

        Returns:
            The encrypted value as a URL-safe base64-encoded string.
        """
        return cls._fernet.encrypt(value.encode()).decode()

    @classmethod
    def decrypt(cls: Type[SecretEncryption], value: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            value: The encrypted base64-encoded string.

        Returns:
            The original decrypted plain text string.
        """
        return cls._fernet.decrypt(value.encode()).decode()
