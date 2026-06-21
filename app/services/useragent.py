"""User-agent parsing into device / browser / OS.

Thin wrapper around the `user-agents` library with a graceful fallback so a
malformed or missing UA string never breaks click tracking.
"""
from __future__ import annotations

from dataclasses import dataclass

from user_agents import parse as _parse


@dataclass(slots=True)
class ParsedUA:
    device_type: str
    browser: str
    os: str


def parse_user_agent(raw: str | None) -> ParsedUA:
    if not raw:
        return ParsedUA(device_type="unknown", browser="unknown", os="unknown")

    try:
        ua = _parse(raw)
    except Exception:  # pragma: no cover - defensive against library edge cases
        return ParsedUA(device_type="unknown", browser="unknown", os="unknown")

    if ua.is_bot:
        device_type = "bot"
    elif ua.is_mobile:
        device_type = "mobile"
    elif ua.is_tablet:
        device_type = "tablet"
    elif ua.is_pc:
        device_type = "desktop"
    else:
        device_type = "other"

    browser = ua.browser.family or "unknown"
    os_family = ua.os.family or "unknown"
    return ParsedUA(device_type=device_type, browser=browser, os=os_family)
