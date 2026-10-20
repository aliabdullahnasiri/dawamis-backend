from app.schemas.base import BaseDataModel


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
