# Contributing

Thanks for taking the time to contribute! This document covers the basics for
getting a development environment running and the conventions used in this repo.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest ruff

# Start dependencies (Postgres + Redis) only:
docker compose up -d postgres redis

export POSTGRES_HOST=localhost REDIS_URL=redis://localhost:6379/0 BASE_URL=http://localhost:8000
alembic upgrade head
uvicorn app.main:app --reload
```

## Before opening a PR

- Format & lint: `ruff format app && ruff check app`
- Run tests: `pytest -q`
- If you changed the schema, add an Alembic migration:
  `alembic revision --autogenerate -m "describe change"`
- Update the README / docs when behaviour changes.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(links): add bulk delete endpoint
fix(redirect): handle expired TTL race condition
chore(deps): bump fastapi to 0.115.6
docs(readme): clarify GeoIP setup
test(analytics): cover empty timeseries
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `ci`.

## Branching

- Branch from `main` using `feat/...`, `fix/...`, or `chore/...`.
- Keep PRs focused and small where possible.
- All PRs must pass CI (lint + tests + docker build) before merge.

## Code style

- Python 3.12, fully type-annotated, `from __future__ import annotations`.
- Business logic lives in `app/services`, HTTP wiring in `app/api`.
- Side-effectful work on the redirect hot path must stay in background tasks.
