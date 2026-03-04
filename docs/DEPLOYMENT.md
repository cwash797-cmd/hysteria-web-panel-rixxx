# Deployment Guide (Ubuntu 24.04)

## Goal

Deploy a self-hosted web panel that manages Hysteria2 users and generates:

- `hy2://` links
- Mihomo YAML files
- QR codes

## Recommended topology

- `hysteria-server` already running on the VPS
- panel app runs locally on `127.0.0.1:8080`
- public access is provided by Cloudflare Tunnel (recommended)

## One-line installation

After publishing this repo to GitHub, installation can be done with:

```bash
curl -fsSL https://raw.githubusercontent.com/<your-org>/<your-repo>/main/scripts/install.sh | \
sudo REPO_URL="https://github.com/<your-org>/<your-repo>.git" \
HWP_PUBLIC_DOMAIN="gprime.mooo.com" \
bash
```

### Useful installer variables

- `HWP_ADMIN_USER`
- `HWP_ADMIN_PASSWORD`
- `HWP_PUBLIC_DOMAIN` (required)
- `HWP_PUBLIC_PORT` (default `443`)
- `HWP_PUBLIC_SNI` (default domain)
- `HWP_HYSTERIA_CONFIG_PATH` (default `/etc/hysteria/config.yaml`)
- `HWP_HYSTERIA_SERVICE_NAME` (default `hysteria-server`)
- `HWP_API_KEYS` (comma-separated API keys for bot/webhook integration)

## Post-install checks

```bash
systemctl status hwp --no-pager
journalctl -u hwp -n 100 --no-pager
curl -s http://127.0.0.1:8080/health
```

## Public access via Cloudflare Tunnel

1. Install and login:

```bash
cloudflared tunnel login
cloudflared tunnel create hwp
```

2. Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: panel.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
```

3. Configure DNS in your authoritative provider:
- `CNAME panel -> <TUNNEL_UUID>.cfargotunnel.com`

4. Run service:

```bash
cloudflared service install
systemctl enable --now cloudflared
systemctl status cloudflared --no-pager
curl -I https://panel.example.com
```

## User experience (what users will see)

1. Admin opens panel URL.
2. Logs in with admin credentials.
3. Adds user: `username + password/token`.
4. Gets:
   - direct `hy2://` link
   - downloadable YAML profile
   - QR for mobile import
5. User imports into Happ Plus/other compatible app and connects.

## Automation flow (Worker -> Panel)

1. Payment webhook hits Cloudflare Worker.
2. Worker validates payment and calls panel `POST /add-client`.
3. Panel creates/updates Hysteria user, restarts service, returns `hy2://` link.
4. Worker sends the link to Telegram user.

## No-downtime operation notes

- Every user change writes `config.yaml` and creates backup copy.
- Panel restarts `hysteria-server` after add/remove.
- Keep at least 512MB free RAM and monitor UDP 443 health.
- Avoid Caddy/Nginx binding to `:443` on same host where Hysteria2 uses `:443`.
