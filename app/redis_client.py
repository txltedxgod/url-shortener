"""Redis connection lifecycle and helpers.

A single shared async client is created on startup and reused everywhere
(connection pooling is handled internally by redis-py).
"""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None


async def init_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        await _redis.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis is not initialised. Call init_redis() first.")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


# --- Cache key helpers -------------------------------------------------------


def cache_key(code: str) -> str:
    return f"link:{code}"


# Sentinel stored in cache to remember that a code does not exist, preventing
# cache-penetration attacks where many requests hit the DB for missing codes.
NOT_FOUND_SENTINEL = "\x00__missing__"
