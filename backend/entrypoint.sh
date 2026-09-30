#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Seeding reference data (statuses, types, priorities)..."
python -m app.scripts.seed_reference

echo "[entrypoint] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
