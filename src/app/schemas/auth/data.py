from datetime import datetime
from uuid import UUID

from app.schemas.base import BaseDataModel


class LoginData(BaseDataModel):
    """
    Authentication data returned after a successful login.
    """

    access_token: str
    refresh_token: str


class RefreshData(BaseDataModel):
    """
    Authentication data returned after refreshing an access token.
    """

    access_token: str


class SessionData(BaseDataModel):
    """
    Data representing a user session.
    """

    id: int
    uuid: UUID
    ip_address: str | None
    user_agent: str | None
    last_used_at: datetime | None
    expires_at: datetime


class TwoFactorSetupData(BaseDataModel):
    """
    Data required to set up two-factor authentication.
    """

    provisioning_uri: str
    qr_code: str


class RecoveryCodesData(BaseDataModel):
    """
    Data containing the user's two-factor authentication recovery codes.
    """

    recovery_codes: list[str]
