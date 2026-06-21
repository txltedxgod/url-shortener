"""Redis-backed sliding-window rate limiter.

Implemented with a sorted set per client: each request is a member scored by
its timestamp. Old entries are trimmed, the window is counted, and a TTL keeps
memory bounded. The whole check is a single atomic Lua script to avoid races.
"""

from __future__ import annotations

import time

from redis.asyncio import Redis

# KEYS[1] = bucket key
# ARGV[1] = now (ms), ARGV[2] = window (ms), ARGV[3] = limit, ARGV[4] = member
# Returns {allowed (0/1), remaining, reset_ms}
_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    return {1, limit - count - 1, window}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local reset = window
if oldest[2] then
    reset = (tonumber(oldest[2]) + window) - now
end
return {0, 0, reset}
"""


class RateLimitResult:
    __slots__ = ("allowed", "remaining", "reset_seconds", "limit")

    def __init__(self, allowed: bool, remaining: int, reset_seconds: float, limit: int):
        self.allowed = allowed
        self.remaining = max(0, remaining)
        self.reset_seconds = max(0.0, reset_seconds)
        self.limit = limit


class RateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int):
        self._redis = redis
        self._limit = limit
        self._window_ms = window_seconds * 1000
        self._script = redis.register_script(_LUA)

    async def hit(self, identifier: str) -> RateLimitResult:
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}-{time.perf_counter_ns()}"
        key = f"ratelimit:{identifier}"
        allowed, remaining, reset_ms = await self._script(
            keys=[key],
            args=[now_ms, self._window_ms, self._limit, member],
        )
        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            reset_seconds=float(reset_ms) / 1000.0,
            limit=self._limit,
        )
