# Hysteria Web Panel v1.0.0

## Highlights

- Initial self-hosted web panel for Hysteria2.
- User management: add/update/remove from `auth.userpass`.
- Access delivery: `hy2://` links, YAML download, QR generation.
- System insights: CPU, RAM, disk, network throughput, service status.
- Manual service action: restart Hysteria from panel.
- Access lifetime controls:
  - default 30-day users
  - `+30d`, `-30d`
  - permanent mode
  - automatic deactivation of expired users
- Bot-ready API endpoint: `POST /add-client` with `X-API-Key`.
- Install helper script and RU/EN documentation.

## Security

- Startup blocked on default admin password.
- Constant-time credential checks.
- `.env` and state files excluded via `.gitignore`.

## Operational notes

- Recommended public access path: Cloudflare Tunnel.
- Keep panel app on `127.0.0.1:8080`.
- Do not bind extra reverse proxies to `:443` on Hysteria host.
