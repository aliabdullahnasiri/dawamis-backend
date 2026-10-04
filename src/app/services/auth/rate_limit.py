from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis

from app.core.config import settings
from app.errors.exceptions import AppError


class AuthRateLimiter:

    @classmethod
    async def check_ip(
        cls: type[AuthRateLimiter],
        redis: Redis,
        ip_address: str,
    ) -> None:
        key = cls._ip_key(ip_address)

        attempts = await redis.get(key)

        if attempts is not None and int(attempts) >= settings.AUTH_RATE_LIMIT_IP:
            raise AppError("auth:too_many_login_attempts")

    @classmethod
    async def check_user(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_id: UUID,
    ) -> None:
        key = cls._user_key(user_id)

        attempts = await redis.get(key)

        if attempts is not None and int(attempts) >= settings.AUTH_RATE_LIMIT_USER:
            raise AppError("auth:too_many_login_attempts")

    @classmethod
    async def record_ip_failure(
        cls: type[AuthRateLimiter],
        redis: Redis,
        ip_address: str,
    ) -> int:
        return await cls._increment(
            redis,
            cls._ip_key(ip_address),
            settings.AUTH_RATE_LIMIT_IP_WINDOW,
        )

    @classmethod
    async def record_user_failure(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_id: UUID,
    ) -> int:
        return await cls._increment(
            redis,
            cls._user_key(user_id),
            settings.AUTH_RATE_LIMIT_USER_WINDOW,
        )

    @classmethod
    async def reset_user(
        cls: type[AuthRateLimiter],
        redis: Redis,
        user_id: UUID,
    ) -> None:
        await redis.delete(cls._user_key(user_id))

    @classmethod
    async def _increment(
        cls: type[AuthRateLimiter],
        redis: Redis,
        key: str,
        window: int,
    ) -> int:
        count = await redis.incr(key)

        if count == 1:
            await redis.expire(key, window)

        return count

    @staticmethod
    def _ip_key(ip_address: str) -> str:
        return f"auth:rate-limit:ip:{ip_address}"

    @staticmethod
    def _user_key(user_id: UUID) -> str:
        return f"auth:rate-limit:user:{user_id}"
