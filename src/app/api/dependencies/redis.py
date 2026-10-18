from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.extensions.redis import redis as redis_client


def get_redis() -> Redis:
    return redis_client


RedisClient = Annotated[Redis, Depends(get_redis)]
