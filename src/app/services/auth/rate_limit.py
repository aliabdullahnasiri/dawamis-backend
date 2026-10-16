from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import RateLimitError


class AuthRateLimiter:
    """
    Service for enforcing rate limits on authentication-related operations.

    Provides mechanisms to track and limit attempts by both IP address and user identity
    to protect against brute-force and DoS attacks.
    """

    @classmethod
    async def check_ip(
        cls: type[AuthRateLimiter],
        redis: Redis,
        ip_address: str,
    ) -> None:
        """
        Check if the given IP address has exceeded the authentication rate limit.

        Args:
            redis: Redis client instance.
            ip_address: The IP address to check.

        Raises:
            RateLimitError: If the IP address is rate-limited.
        """
        key = cls._ip_key(ip_address)

        attempts = await redis.get(key)

        if attempts is not None and int(attempts) >= settings.AUTH_RATE_LIMIT_IP:
            raise RateLimitError()

    @classmethod
    async def check_user(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_uuid: UUID,
    ) -> None:
        """
        Check if the given user has exceeded the authentication rate limit.

        Args:
            redis: Redis client instance.
            user_uuid: The UUID of the user.

        Raises:
            RateLimitError: If the user is rate-limited.
        """
        key = cls._user_key(user_uuid)

        attempts = await redis.get(key)

        if attempts is not None and int(attempts) >= settings.AUTH_RATE_LIMIT_USER:
            raise RateLimitError()

    @classmethod
    async def record_ip_failure(
        cls: type[AuthRateLimiter],
        redis: Redis,
        ip_address: str,
    ) -> int:
        """
        Record a failed authentication attempt for an IP address.

        Args:
            redis: Redis client instance.
            ip_address: The IP address to record.

        Returns:
            The current number of failures for this IP.
        """
        return await cls._increment(
            redis,
            cls._ip_key(ip_address),
            settings.AUTH_RATE_LIMIT_IP_WINDOW,
        )

    @classmethod
    async def record_user_failure(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_uuid: UUID,
    ) -> int:
        """
        Record a failed authentication attempt for a specific user.

        Args:
            redis: Redis client instance.
            user_uuid: The UUID of the user.

        Returns:
            The current number of failures for this user.
        """
        return await cls._increment(
            redis,
            cls._user_key(user_uuid),
            settings.AUTH_RATE_LIMIT_USER_WINDOW,
        )

    @classmethod
    async def reset_user(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_uuid: UUID,
    ) -> None:
        """
        Reset the rate limit counter for a specific user.

        Args:
            redis: Redis client instance.
            user_uuid: The UUID of the user to reset.
        """
        await redis.delete(cls._user_key(user_uuid))

    @classmethod
    async def _increment(
        cls: type[AuthRateLimiter],
        redis: Redis,
        key: str,
        window: int,
    ) -> int:
        """
        Increment the failure counter for a key and set expiration if it's the first attempt.

        Args:
            redis: Redis client instance.
            key: The Redis key to increment.
            window: The expiration window in seconds.

        Returns:
            The updated count of failures.
        """
        count = await redis.incr(key)

        if count == 1:
            await redis.expire(key, window)

        return count

    @staticmethod
    def _ip_key(ip_address: str) -> str:
        """
        Generate a Redis key for IP-based rate limiting.

        Args:
            ip_address: The IP address to key.

        Returns:
            The formatted Redis key.
        """
        return f"auth:rate-limit:ip:{ip_address}"

    @staticmethod
    def _user_key(user_uuid: UUID) -> str:
        """
        Generate a Redis key for user-based rate limiting.

        Args:
            user_uuid: The UUID of the user.

        Returns:
            The formatted Redis key.
        """
        return f"auth:rate-limit:user:{user_uuid}"
