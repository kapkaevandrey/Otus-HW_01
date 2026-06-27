#!/usr/bin/env bash
set -euo pipefail

MONolith_URL="${MONOLITH_URL:-http://localhost:8000}"
CHAT_URL="${CHAT_URL:-http://localhost:8001}"
CHAT_DB_PORT="${CHAT_DB_PORT:-5433}"
PASSWORD="${E2E_PASSWORD:-E2eTest1!Pass}"
MAX_SYNC_WAIT="${MAX_SYNC_WAIT:-30}"

log() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

wait_http() {
  local url=$1 name=$2
  for _ in $(seq 1 60); do
    if curl -sf "$url/api/ping" >/dev/null 2>&1; then
      log "$name is up: $url"
      return 0
    fi
    sleep 2
  done
  fail "$name not ready at $url"
}

wait_user_in_chat_db() {
  local user_id=$1
  for _ in $(seq 1 "$MAX_SYNC_WAIT"); do
    if PGPASSWORD=app_pswd psql -h localhost -p "$CHAT_DB_PORT" -U postgres -d chats -tA \
      -c "SELECT 1 FROM users WHERE id = '$user_id' LIMIT 1;" 2>/dev/null | grep -q 1; then
      log "User $user_id synced to chat DB"
      return 0
    fi
    sleep 1
  done
  fail "User $user_id not synced to chat DB within ${MAX_SYNC_WAIT}s"
}

register_user() {
  local first=$1 second=$2
  curl -sf -X POST "$MONOLITH_URL/api/v1/user/register" \
    -H 'Content-Type: application/json' \
    -d "{\"first_name\":\"$first\",\"second_name\":\"$second\",\"birthdate\":\"1990-05-15\",\"biography\":\"e2e\",\"city\":\"Moscow\",\"password\":\"$PASSWORD\"}"
}

login_user() {
  local user_id=$1
  curl -sf -X POST "$MONOLITH_URL/api/v1/login" \
    -H 'Content-Type: application/json' \
    -d "{\"id\":\"$user_id\",\"password\":\"$PASSWORD\"}"
}

auth_header() {
  local token
  token=$(echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token']['token'])")
  echo "Authorization: Bearer $token"
}

log "Waiting for services..."
wait_http "$MONOLITH_URL" "Monolith"
wait_http "$CHAT_URL" "Chat service"

log "1) Register users on monolith (user sync via outbox + Kafka)"
USER_A_JSON=$(register_user "Alice" "E2e")
USER_B_JSON=$(register_user "Bob" "E2e")
USER_A_ID=$(echo "$USER_A_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
USER_B_ID=$(echo "$USER_B_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
log "Registered Alice=$USER_A_ID Bob=$USER_B_ID"

wait_user_in_chat_db "$USER_A_ID"
wait_user_in_chat_db "$USER_B_ID"

LOGIN_A=$(login_user "$USER_A_ID")
LOGIN_B=$(login_user "$USER_B_ID")
HDR_A=$(auth_header "$LOGIN_A")
HDR_B=$(auth_header "$LOGIN_B")

log "2) Monolith dialog API (proxy to chat-service)"
SEND_MONO=$(curl -sf -X POST "$MONOLITH_URL/api/v1/dialog/$USER_B_ID/send" \
  -H 'Content-Type: application/json' \
  -H "$HDR_A" \
  -d '{"text":"hello via monolith"}')
echo "$SEND_MONO" | python3 -m json.tool
echo "$SEND_MONO" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['sender_id']=='$USER_A_ID', d"

LIST_MONO=$(curl -sf "$MONOLITH_URL/api/v1/dialog/$USER_B_ID/list" -H "$HDR_A")
echo "$LIST_MONO" | python3 -m json.tool
echo "$LIST_MONO" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=1; assert any(m.get('text')=='hello via monolith' or m.get('text') for m in d), d"

log "3) Chat-service dialog API (direct)"
SEND_CHAT=$(curl -sf -X POST "$CHAT_URL/api/v1/dialog/$USER_A_ID/send" \
  -H 'Content-Type: application/json' \
  -H "$HDR_B" \
  -d '{"text":"hello via chat"}')
echo "$SEND_CHAT" | python3 -m json.tool

LIST_CHAT=$(curl -sf "$CHAT_URL/api/v1/dialog/$USER_A_ID/list" -H "$HDR_B")
echo "$LIST_CHAT" | python3 -m json.tool
echo "$LIST_CHAT" | python3 -c "
import sys, json
items = json.load(sys.stdin)
texts = {m.get('text') for m in items}
assert 'hello via monolith' in texts or 'hello via chat' in texts, items
print('Dialog messages OK:', texts)
"

log "All E2E smoke checks passed"
