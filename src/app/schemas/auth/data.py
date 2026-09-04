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
