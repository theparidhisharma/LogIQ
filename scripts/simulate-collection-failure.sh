#!/usr/bin/env sh
# Destructive smoke test: briefly stops Collection, verifies Prometheus sees it down,
# then restores Collection even when the check fails.
set -eu
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
restore() { docker compose start collection >/dev/null 2>&1 || true; }
trap restore EXIT INT TERM
docker compose stop collection
sleep 40
result=$(curl -fsS --get "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=up{job="logiq-apis",instance="collection:8000"}')
printf '%s' "$result" | python -c 'import json,sys; d=json.load(sys.stdin); assert d["data"]["result"] and d["data"]["result"][0]["value"][1] == "0"' || { echo "FAIL: Prometheus did not report Collection down"; exit 1; }
echo "PASS: Prometheus detected Collection outage independently"
restore
trap - EXIT INT TERM
