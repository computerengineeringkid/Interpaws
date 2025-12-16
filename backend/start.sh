#!/bin/bash
set -euo pipefail

# Wait for database and run migrations before starting the API server

RUN_MIGRATIONS_MAX_ATTEMPTS=5
SLEEP_SECONDS=2

attempt=1
while [ $attempt -le $RUN_MIGRATIONS_MAX_ATTEMPTS ]; do
  echo "Running database migrations (attempt ${attempt}/${RUN_MIGRATIONS_MAX_ATTEMPTS})..."
  if alembic upgrade head; then
    echo "Migrations complete. Starting application server."
    break
  fi
  attempt=$((attempt + 1))
  if [ $attempt -le $RUN_MIGRATIONS_MAX_ATTEMPTS ]; then
    echo "Alembic failed; retrying after ${SLEEP_SECONDS}s..."
    sleep $SLEEP_SECONDS
  else
    echo "Alembic migrations failed after ${RUN_MIGRATIONS_MAX_ATTEMPTS} attempts." >&2
    exit 1
  fi
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
