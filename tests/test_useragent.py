"""Unit tests for user-agent parsing."""
from app.services.useragent import parse_user_agent

_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def test_mobile_detection() -> None:
    parsed = parse_user_agent(_IPHONE)
    assert parsed.device_type == "mobile"
    assert parsed.os == "iOS"
    assert parsed.browser in {"Mobile Safari", "Safari"}


def test_desktop_detection() -> None:
    parsed = parse_user_agent(_WINDOWS)
    assert parsed.device_type == "desktop"
    assert parsed.browser == "Chrome"
    assert parsed.os == "Windows"


def test_empty_is_unknown() -> None:
    parsed = parse_user_agent(None)
    assert parsed.device_type == "unknown"
    assert parsed.browser == "unknown"
    assert parsed.os == "unknown"
