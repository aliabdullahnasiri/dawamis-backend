from typing import Self

from pydantic import model_validator

from app.core.exceptions.validation import (
    AuthTokensRequiredError,
    ChallengeTokenForbiddenError,
    ChallengeTokenRequiredError,
)
from app.schemas.base import BaseDataModel


class LoginData(BaseDataModel):
    """
    Authentication data returned after login.

    If 2FA is enabled, returns a temporary challenge token
    instead of normal access and refresh tokens.
    """

    requires_2fa: bool = False

    access_token: str | None = None
    refresh_token: str | None = None

    challenge_token: str | None = None
    expires_in: int | None = None

    @model_validator(mode="after")
    def validate_authentication_state(self: Self) -> Self:
        if self.requires_2fa:
            if not self.challenge_token:
                raise ChallengeTokenRequiredError()

            if self.access_token or self.refresh_token:
                raise ChallengeTokenForbiddenError()

        else:
            if not self.access_token or not self.refresh_token:
                raise AuthTokensRequiredError()

            if self.challenge_token:
                raise ChallengeTokenForbiddenError()

        return self


class RefreshData(BaseDataModel):
    """
    Authentication data returned after refreshing an access token.
    """

    access_token: str
