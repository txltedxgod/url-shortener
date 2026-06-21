"""Click recording and analytics aggregation."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionFactory
from app.logging_config import get_logger
from app.models import Click, Link
from app.services.geoip import get_geoip
from app.services.useragent import parse_user_agent

logger = get_logger(__name__)


@dataclass(slots=True)
class ClickContext:
    """Raw request data captured at redirect time and processed in background."""

    link_id: int
    ip_address: str | None
    referrer: str | None
    user_agent: str | None


async def record_click(ctx: ClickContext) -> None:
    """Persist a click event. Runs in a background task; never blocks redirect.

    Uses its own session because the request-scoped session is already closed
    by the time this executes.
    """
    try:
        ua = parse_user_agent(ctx.user_agent)
        geo = get_geoip().resolve(ctx.ip_address)

        async with SessionFactory() as session:
            click = Click(
                link_id=ctx.link_id,
                ip_address=ctx.ip_address,
                referrer=_normalise_referrer(ctx.referrer),
                user_agent=ctx.user_agent,
                device_type=ua.device_type,
                browser=ua.browser,
                os=ua.os,
                country=geo.country,
                country_code=geo.country_code,
                city=geo.city,
            )
            session.add(click)
            await session.execute(
                update(Link)
                .where(Link.id == ctx.link_id)
                .values(click_count=Link.click_count + 1)
            )
            await session.commit()
    except Exception:  # pragma: no cover - background safety net
        logger.exception("Failed to record click for link_id=%s", ctx.link_id)


def _normalise_referrer(referrer: str | None) -> str | None:
    if not referrer:
        return None
    referrer = referrer.strip()
    return referrer[:2048] if referrer else None


def _referrer_host(referrer: str | None) -> str:
    if not referrer:
        return "direct"
    from urllib.parse import urlparse

    host = urlparse(referrer).netloc
    return host or "direct"


@dataclass(slots=True)
class AnalyticsBundle:
    total_clicks: int
    unique_visitors: int
    timeseries: list[tuple[str, int]]
    top_referrers: list[tuple[str, int]]
    devices: list[tuple[str, int]]
    browsers: list[tuple[str, int]]
    countries: list[tuple[str, int]]


async def build_analytics(
    session: AsyncSession,
    link: Link,
    *,
    days: int = 30,
    bucket: str = "day",
) -> AnalyticsBundle:
    """Aggregate analytics for a single link over a time window."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    base = select(Click).where(
        Click.link_id == link.id, Click.created_at >= since
    ).subquery()

    total = await session.scalar(
        select(func.count()).select_from(base)
    )
    unique = await session.scalar(
        select(func.count(func.distinct(base.c.ip_address))).select_from(base)
    )

    trunc = func.date_trunc(bucket, Click.created_at)
    ts_rows = (
        await session.execute(
            select(trunc.label("bucket"), func.count().label("clicks"))
            .where(Click.link_id == link.id, Click.created_at >= since)
            .group_by(trunc)
            .order_by(trunc)
        )
    ).all()
    timeseries = [
        (r.bucket.date().isoformat() if bucket == "day" else r.bucket.isoformat(), r.clicks)
        for r in ts_rows
    ]

    top_referrers = await _grouped_counts(
        session, link.id, since, Click.referrer, limit=10, transform_host=True
    )
    devices = await _grouped_counts(session, link.id, since, Click.device_type, limit=10)
    browsers = await _grouped_counts(session, link.id, since, Click.browser, limit=10)
    countries = await _grouped_counts(session, link.id, since, Click.country, limit=10)

    return AnalyticsBundle(
        total_clicks=total or 0,
        unique_visitors=unique or 0,
        timeseries=timeseries,
        top_referrers=top_referrers,
        devices=devices,
        browsers=browsers,
        countries=countries,
    )


async def _grouped_counts(
    session: AsyncSession,
    link_id: int,
    since: dt.datetime,
    column,
    *,
    limit: int,
    transform_host: bool = False,
) -> list[tuple[str, int]]:
    label = func.coalesce(column, "unknown")
    rows = (
        await session.execute(
            select(label.label("label"), func.count().label("count"))
            .where(Click.link_id == link_id, Click.created_at >= since)
            .group_by(label)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()
    if transform_host:
        merged: dict[str, int] = {}
        for r in rows:
            host = _referrer_host(r.label if r.label != "unknown" else None)
            merged[host] = merged.get(host, 0) + r.count
        return sorted(merged.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [(r.label, r.count) for r in rows]
