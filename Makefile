.PHONY: help up down logs build migrate revision shell fmt test seed

help:
	@echo "Targets:"
	@echo "  up        - build & start the full stack (api + postgres + redis)"
	@echo "  down      - stop the stack"
	@echo "  logs      - tail api logs"
	@echo "  migrate   - apply migrations inside the api container"
	@echo "  revision  - autogenerate a new migration (m=\"message\")"
	@echo "  seed      - insert demo data"
	@echo "  test      - run the test suite"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec api python -m scripts.seed

shell:
	docker compose exec api bash

fmt:
	ruff format app

test:
	pytest -q
