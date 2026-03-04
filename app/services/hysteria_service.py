from datetime import datetime
from pathlib import Path
from typing import Dict
import shutil
import subprocess
import yaml

from ..config import get_settings


def _load_hysteria_config() -> dict:
    settings = get_settings()
    path = Path(settings.hysteria_config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _save_hysteria_config(data: dict) -> None:
    settings = get_settings()
    path = Path(settings.hysteria_config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Keep timestamped backups before every write.
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = path.with_suffix(f".yaml.bak-{stamp}")
        shutil.copy2(path, backup_path)

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)


def _restart_hysteria_service() -> dict:
    settings = get_settings()
    service = settings.hysteria_service_name
    try:
        subprocess.run(["systemctl", "restart", service], check=True, capture_output=True, text=True)
        return {"ok": True, "message": f"{service} restarted"}
    except FileNotFoundError:
        return {"ok": False, "message": "systemctl not found (likely non-linux environment)"}
    except subprocess.CalledProcessError as e:
        details = e.stderr.strip() if e.stderr else e.stdout.strip()
        return {"ok": False, "message": details or f"Failed to restart {service}"}


def restart_hysteria_service() -> dict:
    return _restart_hysteria_service()


def get_service_status() -> dict:
    settings = get_settings()
    service = settings.hysteria_service_name
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
            check=False,
        )
        return {"service": service, "active_state": result.stdout.strip() or "unknown"}
    except FileNotFoundError:
        return {"service": service, "active_state": "systemctl_unavailable"}


def get_users() -> Dict[str, str]:
    data = _load_hysteria_config()
    auth = data.get("auth", {})
    if auth.get("type") != "userpass":
        return {}
    users = auth.get("userpass") or {}
    return users if isinstance(users, dict) else {}


def get_user_password(username: str) -> str:
    users = get_users()
    password = users.get(username)
    if not password:
        raise KeyError("User not found")
    return password


def add_or_update_user(username: str, password: str, restart_service: bool = True) -> dict:
    data = _load_hysteria_config()
    data.setdefault("auth", {})
    data["auth"]["type"] = "userpass"
    data["auth"].setdefault("userpass", {})
    data["auth"]["userpass"][username] = password
    _save_hysteria_config(data)
    restart = _restart_hysteria_service() if restart_service else {"ok": True, "message": "Restart skipped"}
    return {"user": username, "restart": restart}


def remove_user(username: str, restart_service: bool = True) -> dict:
    data = _load_hysteria_config()
    users = data.get("auth", {}).get("userpass", {})
    if not isinstance(users, dict) or username not in users:
        return {"user": username, "removed": False, "message": "User not found"}
    users.pop(username, None)
    _save_hysteria_config(data)
    restart = _restart_hysteria_service() if restart_service else {"ok": True, "message": "Restart skipped"}
    return {"user": username, "removed": True, "restart": restart}


def remove_users(usernames: list[str], restart_service: bool = True) -> dict:
    data = _load_hysteria_config()
    users = data.get("auth", {}).get("userpass", {})
    if not isinstance(users, dict):
        return {"removed": 0, "users": []}
    removed = []
    for username in usernames:
        if username in users:
            users.pop(username, None)
            removed.append(username)
    if removed:
        _save_hysteria_config(data)
    restart = _restart_hysteria_service() if (restart_service and removed) else {"ok": True, "message": "Restart skipped"}
    return {"removed": len(removed), "users": removed, "restart": restart}


def make_hy2_link(username: str, password: str, domain: str, port: int = 443, sni: str = "") -> str:
    real_sni = sni or domain
    return f"hy2://{username}:{password}@{domain}:{port}?sni={real_sni}#{username}"


def make_mihomo_yaml(username: str, password: str, domain: str, port: int = 443, sni: str = "") -> str:
    real_sni = sni or domain
    return (
        "proxies:\n"
        f"  - name: {username}\n"
        "    type: hysteria2\n"
        f"    server: {domain}\n"
        f"    port: {port}\n"
        f"    password: \"{username}:{password}\"\n"
        f"    sni: {real_sni}\n"
        "    skip-cert-verify: false\n"
        "    up: 120\n"
        "    down: 650\n"
        "\n"
        "proxy-groups:\n"
        "  - name: GLOBAL\n"
        "    type: select\n"
        "    proxies:\n"
        f"      - {username}\n"
        "      - DIRECT\n"
        "\n"
        "rules:\n"
        "  - MATCH,GLOBAL\n"
    )
