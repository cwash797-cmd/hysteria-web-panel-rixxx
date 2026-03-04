from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, Response
from dotenv import load_dotenv
from pathlib import Path
import io
import qrcode

from .auth import login, require_api_key, require_bearer
from .schemas import (
    CreateUserRequest,
    IntegrationIssueRequest,
    LoginRequest,
    LoginResponse,
    RemoveUserRequest,
    RestartServiceRequest,
    UpdateUserAccessRequest,
)
from .config import get_settings
from .services.system_service import get_system_status
from .services.hysteria_service import (
    add_or_update_user,
    get_service_status,
    get_user_password,
    get_users,
    make_hy2_link,
    make_mihomo_yaml,
    remove_user,
    remove_users,
    restart_hysteria_service,
)
from .services.subscription_store import (
    add_user_access_days,
    create_subscription,
    delete_user_access,
    get_expired_usernames,
    get_latest_username_by_tg_id,
    get_user_access,
    init_db,
    list_user_access,
    set_user_access_days,
    set_user_access_permanent,
    upsert_user_access,
)
from secrets import token_hex
import re
from datetime import datetime, UTC
import math


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Hysteria Web Panel", version="0.1.0")
settings = get_settings()


@app.on_event("startup")
def startup_checks() -> None:
    if settings.allow_insecure_defaults:
        return
    if settings.admin_password == "change_me_strong_password":
        raise RuntimeError("Refusing to start with default HWP_ADMIN_PASSWORD")
    init_db()


def _plan_days(plan: str) -> int:
    mapping = {"1m": 30, "3m": 90, "6m": 180}
    if plan in mapping:
        return mapping[plan]
    aliases = {
        "VPN на 1 месяц": 30,
        "VPN на 3 месяца": 90,
        "VPN на 6 месяцев": 180,
    }
    if plan in aliases:
        return aliases[plan]
    raise HTTPException(status_code=400, detail=f"Unsupported plan: {plan}")


def _sanitize_username(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_")
    return value[:32] if value else f"user_{token_hex(3)}"


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _days_left(expires_at_ms: int | None) -> int | None:
    if not expires_at_ms:
        return None
    diff = expires_at_ms - _now_ms()
    return max(math.ceil(diff / 86400000), 0)


def _is_active(meta: dict | None) -> bool:
    if not meta:
        return True
    if int(meta.get("is_permanent", 0)) == 1:
        return True
    exp = meta.get("expires_at_ms")
    return bool(exp and int(exp) > _now_ms())


def _deactivate_expired_users() -> dict:
    expired = get_expired_usernames()
    if not expired:
        return {"removed": 0, "users": []}
    return remove_users(expired, restart_service=True)


def _ensure_user_enabled_state(username: str, restart_service: bool = True) -> dict:
    meta = get_user_access(username)
    if not meta:
        return {"changed": False, "message": "No access metadata"}

    cfg_users = get_users()
    active = _is_active(meta)

    if active and username not in cfg_users:
        add_or_update_user(username, meta["password"], restart_service=restart_service)
        return {"changed": True, "message": "User activated in hysteria config"}
    if (not active) and username in cfg_users:
        remove_user(username, restart_service=restart_service)
        return {"changed": True, "message": "User disabled due to expiry"}
    return {"changed": False, "message": "No changes"}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")


@app.post("/api/auth/login", response_model=LoginResponse)
def auth_login(payload: LoginRequest) -> LoginResponse:
    token, ttl = login(payload.username, payload.password)
    return LoginResponse(access_token=token, expires_in_seconds=ttl)


@app.get("/api/system/status", dependencies=[Depends(require_bearer)])
def system_status() -> dict:
    return get_system_status()


@app.get("/api/hysteria/status", dependencies=[Depends(require_bearer)])
def hysteria_status() -> dict:
    _deactivate_expired_users()
    return get_service_status()


@app.get("/api/hysteria/users", dependencies=[Depends(require_bearer)])
def hysteria_users() -> dict:
    _deactivate_expired_users()
    cfg_users = get_users()
    access_rows = {r["username"]: r for r in list_user_access()}
    all_usernames = sorted(set(cfg_users.keys()) | set(access_rows.keys()))

    users = []
    for username in all_usernames:
        meta = access_rows.get(username)
        if not meta:
            users.append(
                {
                    "username": username,
                    "active": True,
                    "in_config": username in cfg_users,
                    "permanent": True,
                    "expires_at_ms": None,
                    "days_left": None,
                    "managed": False,
                }
            )
            continue
        users.append(
            {
                "username": username,
                "active": _is_active(meta),
                "in_config": username in cfg_users,
                "permanent": int(meta["is_permanent"]) == 1,
                "expires_at_ms": meta["expires_at_ms"],
                "days_left": _days_left(meta["expires_at_ms"]),
                "managed": True,
            }
        )
    return {"users": users}


@app.post("/api/hysteria/users", dependencies=[Depends(require_bearer)])
def hysteria_user_create(payload: CreateUserRequest) -> dict:
    _deactivate_expired_users()
    result = add_or_update_user(payload.username, payload.password, payload.restart_service)
    expiry = None if payload.permanent else (_now_ms() + payload.days * 86400000)
    upsert_user_access(payload.username, payload.password, expiry, payload.permanent)
    if settings.public_domain:
        result["hy2_link"] = make_hy2_link(
            payload.username,
            payload.password,
            settings.public_domain,
            settings.public_port,
            settings.public_sni,
        )
    return result


@app.delete("/api/hysteria/users", dependencies=[Depends(require_bearer)])
def hysteria_user_delete(payload: RemoveUserRequest) -> dict:
    result = remove_user(payload.username, payload.restart_service)
    delete_user_access(payload.username)
    if not result.get("removed"):
        raise HTTPException(status_code=404, detail=result.get("message", "User not found"))
    return result


@app.post("/api/hysteria/restart", dependencies=[Depends(require_bearer)])
def hysteria_restart(payload: RestartServiceRequest) -> dict:
    if not payload.restart_service:
        return {"ok": True, "message": "Restart skipped by request"}
    return restart_hysteria_service()


@app.post("/api/hysteria/users/access", dependencies=[Depends(require_bearer)])
def update_user_access(payload: UpdateUserAccessRequest) -> dict:
    if payload.set_days is not None and payload.add_days is not None:
        raise HTTPException(status_code=400, detail="Use either set_days or add_days, not both")

    row = get_user_access(payload.username)
    if not row:
        try:
            existing_password = get_user_password(payload.username)
        except KeyError:
            raise HTTPException(status_code=404, detail="User not found")
        # Bootstrap legacy users into managed metadata on first access update.
        upsert_user_access(payload.username, existing_password, _now_ms() + 30 * 86400000, False)
        row = get_user_access(payload.username)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to initialize user metadata")

    updated = row
    if payload.set_days is not None:
        updated = set_user_access_days(payload.username, payload.set_days)
    if payload.add_days is not None:
        updated = add_user_access_days(payload.username, payload.add_days)
    if payload.permanent is not None:
        updated = set_user_access_permanent(payload.username, payload.permanent)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update user access")

    sync_result = _ensure_user_enabled_state(payload.username, restart_service=payload.restart_service)
    return {
        "ok": True,
        "user": payload.username,
        "active": _is_active(updated),
        "permanent": int(updated["is_permanent"]) == 1,
        "expires_at_ms": updated["expires_at_ms"],
        "days_left": _days_left(updated["expires_at_ms"]),
        "sync": sync_result,
    }


@app.get("/api/hysteria/users/{username}/link", dependencies=[Depends(require_bearer)])
def get_user_link(username: str) -> dict:
    _deactivate_expired_users()
    if not settings.public_domain:
        raise HTTPException(status_code=400, detail="HWP_PUBLIC_DOMAIN is not configured")
    meta = get_user_access(username)
    if meta and not _is_active(meta):
        raise HTTPException(status_code=403, detail="User is expired/inactive")
    try:
        password = get_user_password(username)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    link = make_hy2_link(username, password, settings.public_domain, settings.public_port, settings.public_sni)
    return {"username": username, "hy2_link": link}


@app.get("/api/hysteria/users/{username}/yaml", dependencies=[Depends(require_bearer)])
def get_user_yaml(username: str) -> PlainTextResponse:
    _deactivate_expired_users()
    if not settings.public_domain:
        raise HTTPException(status_code=400, detail="HWP_PUBLIC_DOMAIN is not configured")
    meta = get_user_access(username)
    if meta and not _is_active(meta):
        raise HTTPException(status_code=403, detail="User is expired/inactive")
    try:
        password = get_user_password(username)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    content = make_mihomo_yaml(username, password, settings.public_domain, settings.public_port, settings.public_sni)
    return PlainTextResponse(
        content=content,
        media_type="text/yaml",
        headers={"Content-Disposition": f"attachment; filename={username}.yaml"},
    )


@app.get("/api/hysteria/users/{username}/qr", dependencies=[Depends(require_bearer)])
def get_user_qr(username: str) -> Response:
    _deactivate_expired_users()
    if not settings.public_domain:
        raise HTTPException(status_code=400, detail="HWP_PUBLIC_DOMAIN is not configured")
    meta = get_user_access(username)
    if meta and not _is_active(meta):
        raise HTTPException(status_code=403, detail="User is expired/inactive")
    try:
        password = get_user_password(username)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    link = make_hy2_link(username, password, settings.public_domain, settings.public_port, settings.public_sni)
    try:
        img = qrcode.make(link)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR generation failed: {e}")


@app.post("/add-client", dependencies=[Depends(require_api_key)])
def integration_add_client(payload: IntegrationIssueRequest) -> dict:
    _deactivate_expired_users()
    if not settings.public_domain:
        raise HTTPException(status_code=400, detail="HWP_PUBLIC_DOMAIN is not configured")

    days = _plan_days(payload.plan)
    order_id = payload.order_id or payload.uuid or payload.email or f"manual_{token_hex(4)}"

    existing_username = payload.username or get_latest_username_by_tg_id(payload.tg_id)
    username_seed = existing_username or payload.email or payload.uuid or f"tg_{payload.tg_id}"
    username = _sanitize_username(username_seed)

    existing_access = get_user_access(username)
    if existing_access:
        password = existing_access["password"]
        updated = add_user_access_days(username, days)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to extend subscription")
        sync_result = _ensure_user_enabled_state(username, restart_service=True)
        expires_at_ms = updated["expires_at_ms"]
        restart_info = {"ok": True, "message": sync_result["message"]}
    else:
        password = payload.password or token_hex(16)
        expires_at_ms = _now_ms() + days * 86400000
        created = add_or_update_user(username, password, restart_service=True)
        upsert_user_access(username, password, expires_at_ms, False)
        restart_info = created.get("restart", {"ok": True, "message": "Restart skipped"})

    link = make_hy2_link(username, password, settings.public_domain, settings.public_port, settings.public_sni)
    create_subscription(username, payload.tg_id, payload.plan, order_id, expires_at_ms)

    return {
        "success": True,
        "message": "client issued",
        "username": username,
        "expiry_ms": expires_at_ms,
        "link": link,
        "restart": restart_info,
    }
