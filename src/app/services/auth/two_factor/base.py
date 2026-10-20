from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class TwoFactorProvider(ABC):
    """
    Abstract base class for Two-Factor Authentication providers.
    """

    @abstractmethod
    async def setup(self, db: AsyncSession, user: User) -> dict[str, Any]:
        """
        Initiate the 2FA setup process for a user.

        Returns:
            A dictionary containing setup data (e.g., QR codes for TOTP).
        """
        pass

    @abstractmethod
    async def verify(self, db: AsyncSession, user: User, code: str) -> bool:
        """
        Verify a 2FA code for a user.

        Returns:
            True if the code is valid, False otherwise.
        """
        pass

    @abstractmethod
    async def enable(self, db: AsyncSession, user: User, code: str) -> None:
        """
        Finalize the enablement of 2FA.

        This is called after the initial setup and a successful verification
        of the first code.
        """
        pass
