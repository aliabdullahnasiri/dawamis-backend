from app.schemas.base import BaseDataModel


class TOTPSetupData(BaseDataModel):
    """
    Data required to set up TOTP authentication.
    """
    provisioning_uri: str
    qr_code: str
