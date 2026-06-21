"""Custom middleware: rate limiting and request id."""
from __future__ import annotations

import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.ratelimit import RateLimiter
from app.dependencies import client_ip
from app.logging_config import get_logger
from app.redis_client import get_redis

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a sliding-window rate limit to write/mutating API endpoints.

    Redirects (GET /{code}) are intentionally exempt so the hot path stays fast;
    they are protected by caching instead.
    """

    _PROTECTED_PREFIXES = ("/api/",)

    def __init__(self, app):
        super().__init__(app)
        self._limiter: RateLimiter | None = None

    def _get_limiter(self) -> RateLimiter:
        if self._limiter is None:
            self._limiter = RateLimiter(
                get_redis(),
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
        return self._limiter

    def _should_limit(self, request: Request) -> bool:
        if not settings.rate_limit_enabled:
            return False
        path = request.url.path
        return any(path.startswith(p) for p in self._PROTECTED_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        if not self._should_limit(request):
            return await call_next(request)

        identifier = client_ip(request) or "anonymous"
        try:
            result = await self._get_limiter().hit(identifier)
        except Exception:  # pragma: no cover - never fail open-closed on Redis blip
            logger.exception("Rate limiter error; allowing request")
            return await call_next(request)

        if not result.allowed:
            retry_after = max(1, int(result.reset_seconds))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
