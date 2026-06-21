"""Validation tests for request schemas."""
import pytest
from pydantic import ValidationError

from app.schemas import ShortenRequest


def test_valid_request() -> None:
    req = ShortenRequest(url="https://example.com/path", alias="my-link", ttl_seconds=3600)
    assert str(req.url).startswith("https://")
    assert req.alias == "my-link"


def test_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        ShortenRequest(url="ftp://example.com")


def test_rejects_bad_alias_chars() -> None:
    with pytest.raises(ValidationError):
        ShortenRequest(url="https://example.com", alias="bad alias!")


def test_rejects_reserved_alias() -> None:
    with pytest.raises(ValidationError):
        ShortenRequest(url="https://example.com", alias="api")


def test_blank_alias_becomes_none() -> None:
    req = ShortenRequest(url="https://example.com", alias="   ")
    assert req.alias is None


def test_ttl_lower_bound() -> None:
    with pytest.raises(ValidationError):
        ShortenRequest(url="https://example.com", ttl_seconds=10)
