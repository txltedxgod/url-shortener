"""Shared FastAPI dependencies and helpers."""

from __future__ import annotations

from fastapi import Request

from app.config import settings


def client_ip(request: Request) -> str | None:
    """Resolve the real client IP, honouring a single reverse proxy hop.

    Trusts X-Forwarded-For only for the left-most entry. In a hardened setup
    you would validate against a list of trusted proxy networks.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


def build_short_url(code: str) -> str:
    return f"{settings.base_url.rstrip('/')}/{code}"


def build_qr_url(code: str) -> str:
    return f"{settings.base_url.rstrip('/')}/api/links/{code}/qr"
