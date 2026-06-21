"""Insert demo links and synthetic click analytics for local exploration.

Run inside the running stack:  make seed
or directly:                   python -m scripts.seed
"""
from __future__ import annotations

import asyncio
import datetime as dt
import random

from sqlalchemy import select

from app.db import SessionFactory
from app.models import Click, Link

_DEMO_URLS = [
    ("github", "https://github.com/txltedxgod"),
    ("docs", "https://fastapi.tiangolo.com/"),
    ("news", "https://news.ycombinator.com/"),
]
_REFERRERS = [
    "https://twitter.com/", "https://www.google.com/", "https://t.co/",
    "https://www.reddit.com/", None,
]
_DEVICES = ["mobile", "desktop", "tablet"]
_BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
_OSES = ["iOS", "Android", "Windows", "Mac OS X", "Linux"]
_COUNTRIES = [
    ("United States", "US"), ("Germany", "DE"), ("Japan", "JP"),
    ("Brazil", "BR"), ("India", "IN"), ("France", "FR"),
]


async def main() -> None:
    async with SessionFactory() as session:
        for code, url in _DEMO_URLS:
            exists = await session.scalar(select(Link).where(Link.code == code))
            if exists:
                continue
            link = Link(code=code, original_url=url, is_custom_alias=True, is_active=True)
            session.add(link)
            await session.flush()

            now = dt.datetime.now(dt.timezone.utc)
            n = random.randint(40, 160)
            for _ in range(n):
                country, cc = random.choice(_COUNTRIES)
                session.add(
                    Click(
                        link_id=link.id,
                        created_at=now - dt.timedelta(days=random.randint(0, 29), hours=random.randint(0, 23)),
                        ip_address=f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
                        referrer=random.choice(_REFERRERS),
                        user_agent="seed",
                        device_type=random.choice(_DEVICES),
                        browser=random.choice(_BROWSERS),
                        os=random.choice(_OSES),
                        country=country,
                        country_code=cc,
                        city=None,
                    )
                )
            link.click_count = n
            print(f"seeded /{code} with {n} clicks")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
