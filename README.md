# Hysteria Web Panel (MVP)

Minimal FastAPI panel for managing Hysteria2 users and viewing server status.

Russian version: `README.ru.md`

## Features

- Admin login with bearer token
- Built-in web UI at `/`
- System status: CPU, RAM, disk, uptime
- Hysteria service status (`systemctl is-active`)
- List users from `auth.userpass`
- Add/update user in `/etc/hysteria/config.yaml`
- Remove user from `/etc/hysteria/config.yaml`
- Auto-generate `hy2://` link per user
- Download user YAML profile
- Generate QR code per user
- Integration endpoint for bots: `POST /add-client` with `X-API-Key`

## Quick Start (local/dev)

1. Create and activate virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure env:

```bash
cp .env.example .env
```

Edit `.env`:

- `HWP_ADMIN_USER`
- `HWP_ADMIN_PASSWORD`
- `HWP_HYSTERIA_CONFIG_PATH`
- `HWP_HYSTERIA_SERVICE_NAME`
- `HWP_PUBLIC_DOMAIN`
- optional: `HWP_PUBLIC_PORT` (default `443`)
- optional: `HWP_PUBLIC_SNI` (default same as domain)
- `HWP_API_KEYS` (comma-separated keys for external bot/webhook calls)

4. Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open Swagger: `http://127.0.0.1:8080/docs`
Open UI: `http://127.0.0.1:8080/`

## One-line install (Ubuntu 24.04)

After this project is pushed to GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/<your-org>/<your-repo>/main/scripts/install.sh | \
sudo REPO_URL="https://github.com/<your-org>/<your-repo>.git" \
HWP_PUBLIC_DOMAIN="gprime.mooo.com" \
bash
```

By default panel binds to `127.0.0.1:8080`. For public access, use Cloudflare Tunnel.

## New server checklist (RU)

See `docs/NEW_SERVER_CHECKLIST_RU.md` for a full "what to change where" list when moving to a new VPS/IP.
See `docs/RELEASE_CHECKLIST_RU.md` before publishing to GitHub.

## API Flow

1. `POST /api/auth/login` to get bearer token.
2. Use token in `Authorization: Bearer <token>`.
3. Call:
   - `GET /api/system/status`
   - `GET /api/hysteria/status`
   - `GET /api/hysteria/users`
   - `POST /api/hysteria/users`
   - `DELETE /api/hysteria/users`
   - `GET /api/hysteria/users/{username}/link`
   - `GET /api/hysteria/users/{username}/yaml`
   - `GET /api/hysteria/users/{username}/qr`

## Bot Integration (Cloudflare Worker compatible)

`POST /add-client` with header:

- `X-API-Key: <one_of_HWP_API_KEYS>`

Body example:

```json
{
  "tg_id": "12345678",
  "plan": "1m",
  "order_id": "trbt_abc123"
}
```

Compatibility note: endpoint also accepts legacy fields `uuid` and `email`.

Response:

```json
{
  "success": true,
  "message": "client issued",
  "username": "tg_12345678_trbt_abc123",
  "expiry_ms": 1773000000000,
  "link": "hy2://...",
  "restart": { "ok": true, "message": "hysteria-server restarted" }
}
```

## Smoke test after deploy

On the server:

```bash
cd /opt/hysteria-web-panel
ADMIN_PASS='<your_admin_password>' PANEL_URL='http://127.0.0.1:8080' bash scripts/smoke_test.sh
```

## Linux Service (optional)

Create `/etc/systemd/system/hwp.service`:

```ini
[Unit]
Description=Hysteria Web Panel
After=network.target

[Service]
WorkingDirectory=/opt/HysteriaWebPanel
ExecStart=/opt/HysteriaWebPanel/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Then:

```bash
systemctl daemon-reload
systemctl enable --now hwp
systemctl status hwp --no-pager
```

## Security Notes

- MVP stores tokens in process memory.
- Run panel behind reverse proxy with HTTPS and basic auth/IP allowlist.
- Restrict panel access to private network or localhost tunnel.
- For production, run this on Linux server where `systemctl` and `/etc/hysteria/config.yaml` are available.
- See detailed hardening in `docs/SECURITY.md`.
- See end-to-end deploy flow in `docs/DEPLOYMENT.md`.
- Keep `.env` and `panel.db` private (already in `.gitignore`).
