"""Short-code generation with collision detection."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import base62
from app.models import Link


class CodeGenerationError(RuntimeError):
    """Raised when a unique code could not be generated."""


async def _code_exists(session: AsyncSession, code: str) -> bool:
    result = await session.execute(select(Link.id).where(Link.code == code).limit(1))
    return result.first() is not None


async def generate_unique_code(session: AsyncSession) -> str:
    """Generate a random base62 code, retrying on collision.

    The code length grows by one after half the retries are exhausted, which
    keeps the keyspace ahead of the number of stored links over time.
    """
    length = settings.shortcode_length
    retries = settings.shortcode_max_retries
    for attempt in range(retries):
        if attempt == retries // 2:
            length += 1
        candidate = base62.random_code(length)
        if not await _code_exists(session, candidate):
            return candidate
    raise CodeGenerationError(
        "could not generate a unique short code; increase SHORTCODE_LENGTH"
    )


async def alias_available(session: AsyncSession, alias: str) -> bool:
    return not await _code_exists(session, alias)
