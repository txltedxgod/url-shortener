#!/usr/bin/env bash
# Container entrypoint: wait for dependencies, run migrations, then exec the CMD.
set -euo pipefail

echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432} ..."
python - <<'PY'
import os, socket, sys, time

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("[entrypoint] PostgreSQL is up")
            sys.exit(0)
    except OSError:
        time.sleep(1)
print("[entrypoint] Timed out waiting for PostgreSQL", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] Running database migrations ..."
alembic upgrade head

echo "[entrypoint] Starting: $*"
exec "$@"
