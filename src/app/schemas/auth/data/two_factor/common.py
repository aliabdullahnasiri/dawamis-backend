from app.schemas.base import BaseDataModel


class RecoveryCodesData(BaseDataModel):
    """
    Data containing the user's two-factor authentication recovery codes.
    """
    recovery_codes: list[str]
