#!/bin/sh
set -e

# Only run migrations for backend service, not for worker
if [ "$ROLE" = "backend" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

echo "Starting application..."
exec "$@"
