from app.schemas.base import BaseDataModel


class TOTPSetupData(BaseDataModel):
    """
    Data required to set up Time-based One-Time Password (TOTP) authentication.
    """

    provisioning_uri: str
    qr_code: str


class RecoveryCodesData(BaseDataModel):
    """
    Data containing the user's two-factor authentication recovery codes.
    """

    recovery_codes: list[str]
