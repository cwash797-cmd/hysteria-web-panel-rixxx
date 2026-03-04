# Security Checklist

## Immediate hardening

- Change admin password in `.env` (never keep defaults).
- Keep panel bound to `127.0.0.1` and expose only via reverse proxy.
- Use HTTPS for panel domain.
- Limit panel access by IP allowlist if possible.

## Service permissions

- The panel runs as root only because it edits `/etc/hysteria/config.yaml` and restarts systemd service.
- For stricter setup, use sudoers rules for specific commands and run panel as dedicated user.

## Network controls

- Open only required ports:
  - `80/tcp` for ACME
  - `443/tcp` and `443/udp` for Hysteria2
  - no direct public `8080` if using reverse proxy

## Logging and audit

- Check panel logs: `journalctl -u hwp -f`
- Check Hysteria logs: `journalctl -u hysteria-server -f`
- Keep backups of `/etc/hysteria/config.yaml` (panel creates timestamped backups before writes).

## Operational safety

- Before major edits, copy config manually:
  - `cp /etc/hysteria/config.yaml /etc/hysteria/config.yaml.manual.bak`
- Test service after changes:
  - `systemctl restart hysteria-server`
  - `systemctl status hysteria-server --no-pager`

## Future improvements

- Add TOTP for admin login.
- Store admin password hash instead of plain `.env`.
- Add per-endpoint rate limiting.
- Add immutable audit log for user actions.
