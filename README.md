# ✂️ URL Shortener with Analytics

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Redis](https://img.shields.io/badge/Redis-7-DC382D)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/txltedxgod/url-shortener/actions/workflows/ci.yml/badge.svg?branch=main)

Production-grade URL shortening service with click analytics, built with **FastAPI (async)**, **PostgreSQL**, **SQLAlchemy 2.0 + Alembic**, and **Redis** (caching + rate limiting). Ships with a single-page vanilla JS dashboard (dark/light theme, Chart.js) and full Docker tooling.

---

## Features

- **`POST /api/shorten`** — shorten a long URL with an optional custom alias and TTL. Codes are generated with **base62**, validated, and checked for collisions (with automatic retry + length growth).
- **`GET /{code}`** — fast redirect served from a **Redis read-through cache**. Click counting happens **in the background** and never blocks the redirect.
- **Per-click analytics** — timestamp, referrer, parsed **user-agent** (device / browser / OS), and **GeoIP** country/city. Persisted asynchronously.
- **Dashboard** — link list, clicks-over-time line chart, top referrers, device/country/browser breakdowns (Chart.js), light/dark theme.
- **QR code** per short link (`GET /api/links/{code}/qr`, PNG).
- **Deactivate / re-activate / delete** links, with cache invalidation.
- **Sliding-window rate limiting** (atomic Redis Lua script) on the API surface.
- Health checks, structured logging, request IDs, graceful lifespan, non-root Docker image.

---

## Architecture

```
           ┌─────────────┐
  client → │  FastAPI    │ ──(cache)──▶  Redis
           │  (async)    │ ──(data)───▶  PostgreSQL
           └──────┬──────┘
                  │ background task
                  ▼
        record click (UA + GeoIP)
```

```
app/
├── main.py            # app factory, lifespan, routing order
├── config.py          # pydantic-settings configuration
├── db.py              # async engine + session factory
├── redis_client.py    # shared async Redis client + cache keys
├── models.py          # Link, Click ORM models
├── schemas.py         # request/response models + validation
├── middleware.py      # rate limiting + request id
├── dependencies.py    # client IP, URL builders
├── core/
│   ├── base62.py      # encode/decode + secure random codes
│   ├── shortcode.py   # unique code generation w/ collision retry
│   └── ratelimit.py   # sliding-window limiter (Lua)
├── services/
│   ├── links.py       # create/resolve/manage links + caching
│   ├── analytics.py   # background click recording + aggregations
│   ├── useragent.py   # UA parsing
│   └── geoip.py       # optional MaxMind GeoLite2 resolver
├── api/
│   ├── links.py       # /api/shorten, /api/links/*
│   ├── qr.py          # /api/links/{code}/qr
│   └── redirect.py    # GET /{code}
└── static/            # dashboard SPA (index.html, style.css, app.js)
```

---

## Quick start (Docker)

```bash
cp .env.example .env          # adjust BASE_URL etc. if needed
docker compose up -d --build   # starts api + postgres + redis
```

The entrypoint waits for PostgreSQL, runs `alembic upgrade head`, then launches Uvicorn.

- Dashboard:  http://localhost:8000/
- API docs:   http://localhost:8000/docs
- Health:     http://localhost:8000/health

Optionally seed demo data:

```bash
make seed
```

---

## Local development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Point these at a local Postgres + Redis (or use docker compose up postgres redis)
export POSTGRES_HOST=localhost REDIS_URL=redis://localhost:6379/0 BASE_URL=http://localhost:8000

alembic upgrade head
uvicorn app.main:app --reload
```

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/shorten` | Create a short link. Body: `{ "url", "alias?", "ttl_seconds?" }` |
| `GET` | `/api/links` | List links (`?limit=&offset=`) |
| `GET` | `/api/links/{code}` | Single link details |
| `GET` | `/api/links/{code}/analytics` | Aggregated analytics (`?days=30`) |
| `GET` | `/api/links/{code}/qr` | PNG QR code |
| `PATCH` | `/api/links/{code}/deactivate` | Disable a link |
| `PATCH` | `/api/links/{code}/activate` | Re-enable a link |
| `DELETE` | `/api/links/{code}` | Delete a link (cascades clicks) |
| `GET` | `/{code}` | Redirect to the original URL |

### Example

```bash
curl -X POST http://localhost:8000/api/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://github.com/txltedxgod", "alias": "gh", "ttl_seconds": 86400}'
```

```json
{
  "code": "gh",
  "short_url": "http://localhost:8000/gh",
  "original_url": "https://github.com/txltedxgod",
  "is_active": true,
  "is_custom_alias": true,
  "click_count": 0,
  "qr_url": "http://localhost:8000/api/links/gh/qr"
}
```

---

## Configuration

All settings come from environment variables (see `.env.example`). Highlights:

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` | Public base used to build short links |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache lifetime for resolved codes |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `60` / `60` | API rate limit |
| `SHORTCODE_LENGTH` | `7` | Length of generated codes |
| `GEOIP_DB_PATH` | _(empty)_ | Path to a MaxMind `GeoLite2-City.mmdb` to enable geo analytics |

### GeoIP (optional)

Geo analytics are disabled until you provide a database. Download `GeoLite2-City.mmdb`
from MaxMind, drop it into `./data/`, and set `GEOIP_DB_PATH=/app/data/GeoLite2-City.mmdb`.
Without it the service runs fine — country/city simply stay empty.

---

## Migrations

```bash
make migrate                       # alembic upgrade head
make revision m="add something"   # autogenerate a new migration
```

---

## Tests

```bash
pip install pytest
pytest -q
```

Unit tests cover base62 round-tripping, user-agent parsing, and request validation.

---

## Push to GitHub

```bash
git init
git add .
git commit -m "feat: production-grade URL shortener with analytics"
git branch -M main
git remote add origin https://github.com/txltedxgod/url-shortener.git
git push -u origin main
```

---

## Notes on design decisions

- **Redirect stays hot:** resolution is cache-first; negative lookups are cached briefly to prevent cache penetration; click writes are backgrounded.
- **Counters vs. truth:** `links.click_count` is a denormalised counter for cheap reads; the `clicks` table is the analytical source of truth.
- **Rate limiting** uses a single atomic Lua script over a Redis sorted set, so it is correct under concurrency and self-expiring.
- **Migrations and runtime share one config** (`app/config.py`), avoiding DSN drift.

---

## License

MIT
