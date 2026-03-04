#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash install.sh"
  exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/your-org/HysteriaWebPanel.git}"
APP_DIR="${APP_DIR:-/opt/hysteria-web-panel}"
SERVICE_NAME="${SERVICE_NAME:-hwp}"
PANEL_PORT="${PANEL_PORT:-8080}"
PANEL_HOST="${PANEL_HOST:-127.0.0.1}"

HWP_ADMIN_USER="${HWP_ADMIN_USER:-admin}"
HWP_ADMIN_PASSWORD="${HWP_ADMIN_PASSWORD:-}"
HWP_PUBLIC_DOMAIN="${HWP_PUBLIC_DOMAIN:-}"
HWP_PUBLIC_PORT="${HWP_PUBLIC_PORT:-443}"
HWP_PUBLIC_SNI="${HWP_PUBLIC_SNI:-}"
HWP_HYSTERIA_CONFIG_PATH="${HWP_HYSTERIA_CONFIG_PATH:-/etc/hysteria/config.yaml}"
HWP_HYSTERIA_SERVICE_NAME="${HWP_HYSTERIA_SERVICE_NAME:-hysteria-server}"
HWP_API_KEYS="${HWP_API_KEYS:-}"

echo "[1/7] Installing OS packages"
apt update -y
apt install -y python3 python3-venv python3-pip git curl

echo "[2/7] Downloading panel source"
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" pull --ff-only
else
  rm -rf "${APP_DIR}"
  git clone "${REPO_URL}" "${APP_DIR}"
fi

echo "[3/7] Creating virtualenv and installing dependencies"
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [[ -z "${HWP_ADMIN_PASSWORD}" ]]; then
  HWP_ADMIN_PASSWORD="$(openssl rand -hex 16)"
fi

if [[ -z "${HWP_API_KEYS}" ]]; then
  HWP_API_KEYS="$(openssl rand -hex 24)"
fi

if [[ -z "${HWP_PUBLIC_DOMAIN}" ]]; then
  echo "HWP_PUBLIC_DOMAIN is required (your Hysteria domain), example: gprime.mooo.com"
  exit 1
fi

if [[ -z "${HWP_PUBLIC_SNI}" ]]; then
  HWP_PUBLIC_SNI="${HWP_PUBLIC_DOMAIN}"
fi

echo "[4/7] Writing .env"
cat > "${APP_DIR}/.env" <<EOF
HWP_ADMIN_USER=${HWP_ADMIN_USER}
HWP_ADMIN_PASSWORD=${HWP_ADMIN_PASSWORD}
HWP_TOKEN_TTL_MINUTES=720
HWP_HYSTERIA_CONFIG_PATH=${HWP_HYSTERIA_CONFIG_PATH}
HWP_HYSTERIA_SERVICE_NAME=${HWP_HYSTERIA_SERVICE_NAME}
HWP_PUBLIC_DOMAIN=${HWP_PUBLIC_DOMAIN}
HWP_PUBLIC_PORT=${HWP_PUBLIC_PORT}
HWP_PUBLIC_SNI=${HWP_PUBLIC_SNI}
HWP_API_KEYS=${HWP_API_KEYS}
HWP_ALLOW_INSECURE_DEFAULTS=false
EOF

echo "[5/7] Creating systemd unit"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Hysteria Web Panel
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host ${PANEL_HOST} --port ${PANEL_PORT}
Restart=always
RestartSec=2
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo "[6/7] Public access recommendation"
echo "Keep panel bound to ${PANEL_HOST}:${PANEL_PORT}."
echo "Use Cloudflare Tunnel (recommended) to expose panel publicly without touching ports 80/443."

echo "[7/7] Done"
echo "Panel service: ${SERVICE_NAME}"
echo "Panel bind: http://${PANEL_HOST}:${PANEL_PORT}"
echo "Admin user: ${HWP_ADMIN_USER}"
echo "Admin password: ${HWP_ADMIN_PASSWORD}"
echo "API key (X-API-Key): ${HWP_API_KEYS}"
echo "Hysteria domain (for links): ${HWP_PUBLIC_DOMAIN}"
