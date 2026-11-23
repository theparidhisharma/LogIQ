#!/usr/bin/env bash
# End-to-end proof against a running stack: ingest a dataset, verify processing,
# persistence, templates, parser selection and anomaly detection. Exits non-zero on any failure.
set -euo pipefail
BASE="${BASE:-http://localhost:8080}"
LINES="${E2E_LINES:-5000}"
BURST="${E2E_BURST:-200}"
SVC="e2e-svc-$(date +%s)"
fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }
json() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

EMAIL="e2e-$(date +%s)@example.com"
PASSWORD="e2e-test-password-123"
TOKEN=$(curl -fsS -X POST "$BASE/v1/auth/register" -H 'content-type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"tenant_name\":\"e2e\"}" | json "d['access_token']") \
  || fail "register"
AUTH=(-H "Authorization: Bearer $TOKEN")
pass "registered tenant user"

APP_ID=$(curl -fsS -X POST "$BASE/v1/applications" "${AUTH[@]}" -H 'content-type: application/json' \
  -d '{"name":"e2e-app","environment":"development"}' | json "d['id']") || fail "create application"
KEY=$(curl -fsS -X POST "$BASE/v1/api-keys" "${AUTH[@]}" -H 'content-type: application/json' \
  -d "{\"label\":\"e2e\",\"application_id\":\"$APP_ID\"}" | json "d['api_key']") || fail "create api key"
pass "created application and ingest key"

# Synthetic HDFS-style dataset: a few fixed templates with varying parameters.
SAMPLE=$(mktemp -t e2e-XXXX).log
awk -v n="$LINES" 'BEGIN{for(i=1;i<=n;i++){
  printf "2026-11-20T07:%02d:%02dZ INFO dfs.DataNode blk_%d served to /10.0.%d.%d\n", int(i/60)%60, i%60, 1000000+i, i%255, (i*7)%255;
  if(i%5==0) printf "2026-11-20T07:%02d:%02dZ WARN dfs.FSNamesystem replication of blk_%d is slow\n", int(i/60)%60, i%60, 1000000+i;
}}' > "$SAMPLE"
EXPECTED=$(wc -l < "$SAMPLE" | tr -d ' ')
DS_ID=$(curl -fsS -X POST "$BASE/v1/datasets/upload" -H "X-API-Key: $KEY" \
  -F "file=@$SAMPLE;filename=e2e-hdfs.log;type=text/plain" | json "d['dataset_id']") || fail "upload"
pass "uploaded dataset $DS_ID ($EXPECTED lines)"

STATUS=""
for _ in $(seq 1 180); do
  STATUS=$(curl -fsS "$BASE/v1/datasets/$DS_ID" -H "X-API-Key: $KEY" | json "d['status']")
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && fail "dataset processing failed: $(curl -fsS "$BASE/v1/datasets/$DS_ID" -H "X-API-Key: $KEY" | json "d['error_message']")"
  sleep 5
done
[ "$STATUS" = "completed" ] || fail "dataset did not complete within 15 minutes (status=$STATUS)"
pass "dataset completed"

TOTAL=$(curl -fsS "$BASE/v1/logs?dataset_id=$DS_ID&include_total=true&limit=1" "${AUTH[@]}" | json "d['total']")
[ "$TOTAL" = "$EXPECTED" ] || fail "persisted log count $TOTAL != uploaded lines $EXPECTED"
pass "all $TOTAL lines persisted and searchable"

TEMPLATES=$(curl -fsS "$BASE/v1/templates?limit=5" "${AUTH[@]}" | json "d['total']")
[ "$TEMPLATES" -ge 1 ] || fail "no templates discovered"
pass "$TEMPLATES templates discovered"

SELECTED=$(curl -fsS "$BASE/v1/datasets/$DS_ID/benchmark" -H "X-API-Key: $KEY" | json "d.get('selected_parser')")
[ "$SELECTED" != "None" ] && [ -n "$SELECTED" ] || fail "no parser selected"
pass "parser selected: $SELECTED"

# Error burst for a dedicated service; expect an error-frequency anomaly.
python3 -c "
import json,datetime
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps({'logs':[{'message':f'payment gateway timeout {i}','severity':'ERROR','service_name':'$SVC','timestamp':now} for i in range($BURST)]}))" > "$SAMPLE.json"
curl -fsS -X POST "$BASE/v1/logs" -H "X-API-Key: $KEY" -H 'content-type: application/json' --data @"$SAMPLE.json" >/dev/null || fail "error burst ingestion"
FOUND=0
for _ in $(seq 1 24); do
  COUNT=$(curl -fsS "$BASE/v1/anomalies?kind=error_frequency_spike&service=$SVC" "${AUTH[@]}" | json "d['total']")
  if [ "$COUNT" -ge 1 ]; then FOUND=1; break; fi
  sleep 5
done
[ "$FOUND" = 1 ] || fail "no error_frequency_spike anomaly for service $SVC within 2 minutes"
pass "error burst detected as anomaly"

rm -f "$SAMPLE" "$SAMPLE.json"
echo "ALL E2E CHECKS PASSED"
