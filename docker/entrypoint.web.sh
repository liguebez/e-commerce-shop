#!/bin/sh
set -eu

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "[web] waiting for postgres at ${DB_HOST}:${DB_PORT}..."
i=0
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "[web] postgres still unreachable after 60s, aborting" >&2
        exit 1
    fi
    sleep 2
done
echo "[web] postgres is accepting connections"

echo "[web] running migrations..."
python manage.py migrate --noinput

echo "[web] starting: $*"
exec "$@"
