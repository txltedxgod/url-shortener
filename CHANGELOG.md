# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned
- Background job to purge expired links and their analytics.
- Custom domain support for short links.
- Optional API-key auth for the management endpoints.

## [1.0.0] - 2026-01-01

### Added
- `POST /api/shorten` with base62 code generation, collision retry, custom
  aliases, and TTL.
- `GET /{code}` redirect served from a Redis read-through cache with background
  click tracking.
- Per-click analytics: referrer, user-agent parsing (device/browser/OS), and
  optional GeoIP country/city.
- Analytics aggregation endpoint and a single-page dashboard (Chart.js, dark/
  light theme).
- QR code generation per short link.
- Link deactivate / activate / delete with cache invalidation.
- Sliding-window rate limiting backed by an atomic Redis Lua script.
- Dockerfile (multi-stage, non-root), docker-compose stack, Alembic migrations,
  health checks, structured logging, and a test suite.

[Unreleased]: https://github.com/txltedxgod/url-shortener/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/txltedxgod/url-shortener/releases/tag/v1.0.0
