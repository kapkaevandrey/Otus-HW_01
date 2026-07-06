#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker-compose -f $ROOT/test_infra/docker-compose.yaml"
REPORT_DIR="$ROOT/test_infra/k6_reports"
mkdir -p "$REPORT_DIR"
LOG="$REPORT_DIR/hw_run.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== 1) Start infra (3 app instances) ==="
cd "$ROOT"
$COMPOSE down --remove-orphans 2>/dev/null || true
APP_INSTANCES=3 $COMPOSE up -d --build --scale app=3 2>&1 | tee -a "$LOG"

log "=== 2) Wait for stack ==="
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8000/livez >/dev/null 2>&1; then
    log "API is ready"
    break
  fi
  sleep 5
done
curl -fsS http://localhost:8000/livez | tee -a "$LOG"

log "=== 3) Generate users (may take several minutes) ==="
uv run test_infra/scripts/generate_users.py 2>&1 | tee -a "$LOG"

log "=== 4) Verify users in DB ==="
COUNT=$(docker exec patroni1 psql -h 127.0.0.1 -U postgres -d app_db -tA -c "SELECT count(*) FROM users;")
log "users count in DB: $COUNT"
if [ "$COUNT" -lt 1000 ]; then
  echo "ERROR: expected users in DB" | tee -a "$LOG"
  exit 1
fi

SAMPLE_ID=$(python3 -c 'import json; print(json.load(open("test_infra/scripts/user_ids.json"))[0])')
SAMPLE_SEARCH=$(python3 -c 'import json; p=json.load(open("test_infra/scripts/search_pairs.json"))[0]; print(p["first_name"], p["last_name"])')
read -r FIRST_NAME LAST_NAME <<< "$SAMPLE_SEARCH"

log "=== 5) Manual API checks ==="
curl -fsS "http://localhost:8000/api/v1/user/get/${SAMPLE_ID}" | tee -a "$LOG"
echo | tee -a "$LOG"
curl -fsS "http://localhost:8000/api/v1/user/search?first_name=${FIRST_NAME}&last_name=${LAST_NAME}" | head -c 300 | tee -a "$LOG"
echo | tee -a "$LOG"

log "=== 6) Start 10-minute k6 load test ==="
$COMPOSE --profile loadtest run --rm --name k6_hw k6 run /scripts/load_read_users.js 2>&1 | tee "$REPORT_DIR/k6_hw.log" &
K6_PID=$!

log "=== 7) At 6 min: kill app instance ==="
sleep 360
APP_TARGET=$(docker ps --format '{{.Names}}' | grep 'test_infra-app-' | head -1)
log "Killing app container: $APP_TARGET"
docker update --restart=no "$APP_TARGET" >/dev/null
docker kill -s KILL "$APP_TARGET" 2>&1 | tee -a "$LOG"
docker ps --format '{{.Names}} {{.Status}}' | grep app | tee -a "$LOG"

log "=== 8) At 8 min: kill PostgreSQL replica patroni2 ==="
sleep 120
log "Killing patroni2"
docker kill -s KILL patroni2 2>&1 | tee -a "$LOG"
docker exec patroni1 patronictl -c /etc/patroni.yml list 2>&1 | tee -a "$LOG"

log "=== 9) Wait for k6 to finish ==="
wait "$K6_PID" || true
log "Done. Logs: $LOG and $REPORT_DIR/k6_hw.log"
