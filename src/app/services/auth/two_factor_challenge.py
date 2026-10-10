from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Type
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError
from redis.asyncio import Redis

from app.core.config import settings
from app.core.i18n.types import T
from app.schemas.auth.two_factor import TwoFactorChallengePayload


@dataclass(frozen=True, slots=True)
class TwoFactorChallenge:
    user_id: str
    challenge_id: str
    expires_at: datetime


class TwoFactorChallengeService:
    PREFIX = "auth:2fa:challenge:"
    TTL_SECONDS = 300

    _CONSUME_SCRIPT = """
    local value = redis.call('GET', KEYS[1])

    if value == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    end

    return 0
    """

    @classmethod
    def _key(cls, challenge_id: str) -> str:
        return f"{cls.PREFIX}{challenge_id}"

    @classmethod
    def _encode_token(
        cls: Type[TwoFactorChallengeService],
        user_id: str,
        challenge_id: str,
        expires_at: datetime,
    ) -> str:
        now = datetime.now(UTC)

        payload: dict[str, Any] = {
            "sub": user_id,
            "jti": challenge_id,
            "purpose": "2fa_challenge",
            "iat": now,
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    async def create(
        cls: Type[TwoFactorChallengeService],
        redis: Redis,
        user_id: str | int,
    ) -> str:
        """Create a temporary challenge after password verification."""
        normalized_user_id = str(user_id)
        challenge_id = uuid4().hex
        expires_at = datetime.now(UTC) + timedelta(seconds=cls.TTL_SECONDS)

        token = cls._encode_token(
            user_id=normalized_user_id,
            challenge_id=challenge_id,
            expires_at=expires_at,
        )

        created = await redis.set(
            cls._key(challenge_id),
            normalized_user_id,
            ex=cls.TTL_SECONDS,
            nx=True,
        )

        if not created:
            raise RuntimeError(T("auth:failed_to_create_2fa_challenge"))

        return token

    @classmethod
    async def validate(
        cls: Type[TwoFactorChallengeService],
        redis: Redis,
        token: str,
    ) -> TwoFactorChallenge:
        """Validate the token and check that its challenge is active."""
        try:

            payload: TwoFactorChallengePayload = (
                TwoFactorChallengePayload.model_validate(
                    jwt.decode(
                        token,
                        settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={
                            "require": [
                                "sub",
                                "jti",
                                "purpose",
                                "iat",
                                "exp",
                            ],
                        },
                    )
                )
            )

        except InvalidTokenError, ValidationError:
            raise ValueError(T("auth:invalid_two_factor_challenge"))

        user_id = payload.sub
        challenge_id = payload.jti
        expires_timestamp = payload.exp

        stored_user_id = await redis.get(cls._key(challenge_id))

        if stored_user_id is None:
            raise ValueError(T("auth:two_factor_challenge_expired"))

        if isinstance(stored_user_id, bytes):
            stored_user_id = stored_user_id.decode()

        if stored_user_id != user_id:
            raise ValueError(T("auth:invalid_two_factor_challenge"))

        return TwoFactorChallenge(
            user_id=user_id,
            challenge_id=challenge_id,
            expires_at=datetime.fromtimestamp(
                expires_timestamp,
                tz=UTC,
            ),
        )

    @classmethod
    async def consume(
        cls: Type[TwoFactorChallengeService],
        redis: Redis,
        challenge: TwoFactorChallenge,
    ) -> bool:
        """Invalidate a challenge atomically; succeed only once."""
        result = await redis.eval(
            cls._CONSUME_SCRIPT,
            1,
            cls._key(challenge.challenge_id),
            challenge.user_id,
        )

        return bool(result)
