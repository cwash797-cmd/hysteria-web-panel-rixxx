#!/usr/bin/env bash
set -euo pipefail

# Usage:
# PANEL_URL=http://127.0.0.1:8080 ADMIN_USER=admin ADMIN_PASS=... bash scripts/smoke_test.sh

PANEL_URL="${PANEL_URL:-http://127.0.0.1:8080}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-}"

if [[ -z "${ADMIN_PASS}" ]]; then
  echo "ADMIN_PASS is required"
  exit 1
fi

echo "[1/7] Health"
curl -fsS "${PANEL_URL}/health" >/dev/null
echo "OK"

echo "[2/7] Login"
LOGIN_JSON="$(curl -fsS -X POST "${PANEL_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}")"
TOKEN="$(echo "${LOGIN_JSON}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')"
if [[ -z "${TOKEN}" ]]; then
  echo "Failed to get token"
  exit 1
fi
echo "OK"

TEST_USER="smoke_$(date +%s)"
TEST_PASS="$(openssl rand -hex 8)"

echo "[3/7] Create user ${TEST_USER}"
curl -fsS -X POST "${PANEL_URL}/api/hysteria/users" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_USER}\",\"password\":\"${TEST_PASS}\",\"restart_service\":true}" >/dev/null
echo "OK"

echo "[4/7] Get user link"
LINK_JSON="$(curl -fsS "${PANEL_URL}/api/hysteria/users/${TEST_USER}/link" -H "Authorization: Bearer ${TOKEN}")"
LINK_VAL="$(echo "${LINK_JSON}" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("hy2_link",""))')"
if [[ "${LINK_VAL}" != hy2://* ]]; then
  echo "Invalid hy2 link: ${LINK_VAL}"
  exit 1
fi
echo "OK: ${LINK_VAL}"

echo "[5/7] Download YAML"
curl -fsS "${PANEL_URL}/api/hysteria/users/${TEST_USER}/yaml" -H "Authorization: Bearer ${TOKEN}" >/dev/null
echo "OK"

echo "[6/7] Download QR"
curl -fsS "${PANEL_URL}/api/hysteria/users/${TEST_USER}/qr" -H "Authorization: Bearer ${TOKEN}" >/dev/null
echo "OK"

echo "[7/7] Delete user"
curl -fsS -X DELETE "${PANEL_URL}/api/hysteria/users" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_USER}\",\"restart_service\":true}" >/dev/null
echo "OK"

echo "Smoke test passed."
