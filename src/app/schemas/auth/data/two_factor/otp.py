from app.schemas.base import BaseDataModel


class OTPSetupData(BaseDataModel):
    """
    Data required to set up OTP authentication.
    """
    message: str
