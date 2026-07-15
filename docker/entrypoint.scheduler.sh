#!/bin/sh
set -eu

INTERVAL="${RELEASE_EXPIRED_ORDERS_INTERVAL_SECONDS:-300}"
echo "[scheduler] release_expired_orders loop starting, interval=${INTERVAL}s"

while true; do
    python manage.py release_expired_orders || echo "[scheduler] run failed, will retry next interval" >&2
    sleep "$INTERVAL"
done
