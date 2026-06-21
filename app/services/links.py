"""Business logic for creating, resolving and managing links."""
from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import shortcode
from app.logging_config import get_logger
from app.models import Link
from app.redis_client import NOT_FOUND_SENTINEL, cache_key, get_redis
from app.schemas import ShortenRequest

logger = get_logger(__name__)


class AliasTakenError(Exception):
    """Raised when a requested custom alias is already in use."""


class LinkNotFoundError(Exception):
    """Raised when a link cannot be found."""


async def create_link(session: AsyncSession, payload: ShortenRequest) -> Link:
    expires_at: dt.datetime | None = None
    if payload.ttl_seconds:
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            seconds=payload.ttl_seconds
        )

    original_url = str(payload.url)

    if payload.alias:
        if not await shortcode.alias_available(session, payload.alias):
            raise AliasTakenError(payload.alias)
        code = payload.alias
        is_custom = True
    else:
        code = await shortcode.generate_unique_code(session)
        is_custom = False

    link = Link(
        code=code,
        original_url=original_url,
        is_custom_alias=is_custom,
        is_active=True,
        expires_at=expires_at,
    )
    session.add(link)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Concurrent insert won the race for this code/alias.
        await session.rollback()
        if is_custom:
            raise AliasTakenError(code) from exc
        # Extremely unlikely random collision; retry once with a fresh code.
        link.code = await shortcode.generate_unique_code(session)
        session.add(link)
        await session.commit()

    await session.refresh(link)
    logger.info("Created link code=%s custom=%s", link.code, is_custom)
    return link


async def resolve_code(session: AsyncSession, code: str) -> str | None:
    """Resolve a code to its original URL, using Redis as a read-through cache.

    Returns the original URL, or None if the code is missing / inactive /
    expired. Negative lookups are cached briefly to prevent cache penetration.
    """
    redis = get_redis()
    key = cache_key(code)

    cached = await redis.get(key)
    if cached is not None:
        if cached == NOT_FOUND_SENTINEL:
            return None
        return cached

    link = await session.scalar(select(Link).where(Link.code == code))
    if link is None or not link.is_active or link.is_expired:
        # Cache the miss for a short time.
        await redis.set(key, NOT_FOUND_SENTINEL, ex=min(settings.cache_ttl_seconds, 60))
        return None

    ttl = settings.cache_ttl_seconds
    if link.expires_at is not None:
        remaining = int(
            (link.expires_at - dt.datetime.now(dt.timezone.utc)).total_seconds()
        )
        if remaining <= 0:
            return None
        ttl = min(ttl, remaining)

    await redis.set(key, link.original_url, ex=ttl)
    return link.original_url


async def get_link(session: AsyncSession, code: str) -> Link:
    link = await session.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise LinkNotFoundError(code)
    return link


async def list_links(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[Link], int]:
    total = await session.scalar(select(func.count()).select_from(Link)) or 0
    rows = (
        await session.scalars(
            select(Link).order_by(Link.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    return list(rows), total


async def set_active(session: AsyncSession, code: str, *, active: bool) -> Link:
    link = await get_link(session, code)
    link.is_active = active
    await session.commit()
    await session.refresh(link)
    await _invalidate_cache(code)
    logger.info("Set link code=%s active=%s", code, active)
    return link


async def delete_link(session: AsyncSession, code: str) -> None:
    link = await get_link(session, code)
    await session.delete(link)
    await session.commit()
    await _invalidate_cache(code)
    logger.info("Deleted link code=%s", code)


async def _invalidate_cache(code: str) -> None:
    try:
        await get_redis().delete(cache_key(code))
    except Exception:  # pragma: no cover - cache invalidation is best-effort
        logger.warning("Failed to invalidate cache for code=%s", code)
