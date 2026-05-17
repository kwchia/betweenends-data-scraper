#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null; do
  sleep 1
done

echo "Running migrations..."
flask db upgrade

echo "Ensuring default admin account..."
flask ensure-admin

exec "$@"
