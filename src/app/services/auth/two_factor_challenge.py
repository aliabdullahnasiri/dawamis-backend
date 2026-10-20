from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError
from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions.authentication import (
    InvalidTwoFactorChallengeError,
    TwoFactorChallengeExpiredError,
)
from app.schemas.auth.internal.two_factor import TwoFactorChallengePayload


@dataclass(frozen=True, slots=True)
class TwoFactorChallenge:
    """
    Represents a Two-Factor authentication challenge.

    Attributes:
        user_id: The ID of the user for whom the challenge was created.
        challenge_id: A unique identifier for the specific challenge instance.
        expires_at: The expiration timestamp of the challenge.
    """
    user_id: str
    challenge_id: str
    expires_at: datetime


class TwoFactorChallengeService:
    """
    Service for managing temporary Two-Factor authentication challenges.

    This service handles the creation, validation, and consumption of
    short-lived challenges used during the 2FA verification process.
    """
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
        """
        Generate the Redis key for a given challenge ID.

        Args:
            challenge_id: The unique identifier of the challenge.

        Returns:
            The formatted Redis key string.
        """
        return f"{cls.PREFIX}{challenge_id}"


    @classmethod
    def _encode_token(
        cls: type[TwoFactorChallengeService],
        user_id: str,
        challenge_id: str,
        expires_at: datetime,
    ) -> str:
        """
        Encode a challenge into a JWT token.

        Args:
            user_id: The ID of the user.
            challenge_id: The unique identifier for the challenge.
            expires_at: The expiration timestamp.

        Returns:
            An encoded JWT string representing the challenge.
        """
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
        cls: type[TwoFactorChallengeService],
        redis: Redis,
        user_id: str | int,
    ) -> str:
        """
        Create a temporary 2FA challenge after successful password verification.

        The challenge is stored in Redis and a signed JWT is returned to the client.

        Args:
            redis: Redis client instance.
            user_id: The ID of the user.

        Returns:
            A JWT token that can be used to validate the challenge.

        Raises:
            RuntimeError: If the challenge failed to be created in Redis.
        """
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
            raise RuntimeError("Failed to create 2FA challenge in Redis")


        return token

    @classmethod
    async def validate(
        cls: type[TwoFactorChallengeService],
        redis: Redis,
        token: str,
    ) -> TwoFactorChallenge:
        """
        Validate the 2FA challenge token and ensure the challenge is still active.

        Args:
            redis: Redis client instance.
            token: The JWT challenge token to validate.

        Returns:
            A TwoFactorChallenge object containing the challenge details.

        Raises:
            ValueError: If the token is invalid, expired, or the challenge is inactive.
        """
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
            raise InvalidTwoFactorChallengeError()


        user_id = payload.sub
        challenge_id = payload.jti
        expires_timestamp = payload.exp

        stored_user_id = await redis.get(cls._key(challenge_id))

        if stored_user_id is None:
            raise TwoFactorChallengeExpiredError()


        if isinstance(stored_user_id, bytes):
            stored_user_id = stored_user_id.decode()

        if stored_user_id != user_id:
            raise InvalidTwoFactorChallengeError()


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
        cls: type[TwoFactorChallengeService],
        redis: Redis,
        challenge: TwoFactorChallenge,
    ) -> bool:
        """
        Atomically invalidate a challenge to prevent replay attacks.

        Args:
            redis: Redis client instance.
            challenge: The TwoFactorChallenge object to consume.

        Returns:
            True if the challenge was successfully consumed, False otherwise.
        """
        result = await redis.eval(

            cls._CONSUME_SCRIPT,
            1,
            cls._key(challenge.challenge_id),
            challenge.user_id,
        )

        return bool(result)
