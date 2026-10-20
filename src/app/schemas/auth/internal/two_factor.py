from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, field_validator

from app.core.exceptions.validation import InvalidTimestampError
from app.schemas.base.model import Model as BaseModel


class TwoFactorChallengePayload(BaseModel):
    __extra__ = "ignore"

    sub: str = Field(min_length=1)
    jti: str = Field(min_length=1)
    purpose: Literal["2fa_challenge"]
    exp: int | float
    iat: int | float

    @field_validator("exp", "iat")
    @classmethod
    def validate_timestamp(
        cls: type[TwoFactorChallengePayload], value: float
    ) -> int | float:
        if not datetime.fromtimestamp(value, tz=UTC):
            raise InvalidTimestampError()

        return value
