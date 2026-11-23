#!/usr/bin/env sh
# Run while the LogIQ Compose stack is up. A non-zero exit means a check failed.
set -eu
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
COLLECTION_URL="${COLLECTION_URL:-http://localhost:8001}"
check() {
  name="$1"; url="$2"
  code=$(curl -sS -o /tmp/logiq-observability-check.out -w '%{http_code}' "$url" || true)
  if [ "$code" != "200" ]; then echo "FAIL $name (HTTP $code)"; return 1; fi
  echo "PASS $name"
}
check "Collection health" "$COLLECTION_URL/health"
check "Prometheus ready" "$PROMETHEUS_URL/-/ready"
query=$(curl -fsS --get "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=up{job="logiq-apis",instance="collection:8000"}')
printf '%s' "$query" | python -c 'import json,sys; d=json.load(sys.stdin); assert d["data"]["result"] and d["data"]["result"][0]["value"][1] == "1"'
echo "PASS Prometheus independently scrapes Collection"
