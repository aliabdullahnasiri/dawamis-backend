from app.schemas.base import BaseDataModel


class TokenData(BaseDataModel):
    """
    Schema representing a set of authentication tokens.
    """

    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = "Bearer"
