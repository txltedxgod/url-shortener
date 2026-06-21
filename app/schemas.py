"""Pydantic request/response schemas."""
from __future__ import annotations

import datetime as dt
import re

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.config import settings

_ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]+$")
# Aliases that would collide with real API routes.
_RESERVED_ALIASES = {
    "api", "shorten", "docs", "redoc", "openapi.json", "health",
    "static", "admin", "dashboard", "favicon.ico", "qr",
}


class ShortenRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: AnyHttpUrl = Field(..., description="The long URL to shorten.")
    alias: str | None = Field(
        default=None,
        description="Optional custom alias. Must be URL-safe.",
    )
    ttl_seconds: int | None = Field(
        default=None,
        ge=60,
        le=60 * 60 * 24 * 365,
        description="Optional time-to-live in seconds.",
    )

    @field_validator("alias")
    @classmethod
    def _validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not (settings.alias_min_length <= len(value) <= settings.alias_max_length):
            raise ValueError(
                f"alias must be between {settings.alias_min_length} and "
                f"{settings.alias_max_length} characters"
            )
        if not _ALIAS_RE.match(value):
            raise ValueError(
                "alias may only contain letters, digits, '-' and '_'"
            )
        if value.lower() in _RESERVED_ALIASES:
            raise ValueError("alias is reserved")
        return value


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    short_url: str
    original_url: str
    is_active: bool
    is_custom_alias: bool
    click_count: int
    created_at: dt.datetime
    expires_at: dt.datetime | None
    qr_url: str


class LinkListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    short_url: str
    original_url: str
    is_active: bool
    click_count: int
    created_at: dt.datetime
    expires_at: dt.datetime | None
    qr_url: str


class LinkList(BaseModel):
    items: list[LinkListItem]
    total: int
    limit: int
    offset: int


class TimeseriesPoint(BaseModel):
    bucket: str
    clicks: int


class LabelCount(BaseModel):
    label: str
    count: int


class LinkAnalytics(BaseModel):
    code: str
    total_clicks: int
    unique_visitors: int
    timeseries: list[TimeseriesPoint]
    top_referrers: list[LabelCount]
    devices: list[LabelCount]
    browsers: list[LabelCount]
    countries: list[LabelCount]


class MessageResponse(BaseModel):
    detail: str
