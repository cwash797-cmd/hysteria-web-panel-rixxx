from pathlib import Path
import sqlite3
from datetime import datetime, UTC
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "panel.db"


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                tg_id TEXT,
                plan TEXT,
                order_id TEXT,
                expires_at_ms INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_tg_id ON subscriptions(tg_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_username ON subscriptions(username)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_access (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                expires_at_ms INTEGER,
                is_permanent INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_subscription(username: str, tg_id: str, plan: str, order_id: str, expires_at_ms: int) -> None:
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO subscriptions (username, tg_id, plan, order_id, expires_at_ms, created_at_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, tg_id, plan, order_id, expires_at_ms, now_ms),
        )
        conn.commit()
    finally:
        conn.close()


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def upsert_user_access(username: str, password: str, expires_at_ms: int | None, is_permanent: bool) -> None:
    now_ms = _now_ms()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO user_access (username, password, expires_at_ms, is_permanent, created_at_ms, updated_at_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
              password=excluded.password,
              expires_at_ms=excluded.expires_at_ms,
              is_permanent=excluded.is_permanent,
              updated_at_ms=excluded.updated_at_ms
            """,
            (username, password, expires_at_ms, 1 if is_permanent else 0, now_ms, now_ms),
        )
        conn.commit()
    finally:
        conn.close()


def delete_user_access(username: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM user_access WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()


def get_user_access(username: str) -> dict[str, Any] | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT username, password, expires_at_ms, is_permanent, created_at_ms, updated_at_ms FROM user_access WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_user_access() -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT username, password, expires_at_ms, is_permanent, created_at_ms, updated_at_ms FROM user_access ORDER BY username ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_user_access_days(username: str, days: int) -> dict[str, Any] | None:
    row = get_user_access(username)
    if not row:
        return None
    now_ms = _now_ms()
    expires_at_ms = now_ms + days * 86400000
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_access SET expires_at_ms = ?, is_permanent = 0, updated_at_ms = ? WHERE username = ?",
            (expires_at_ms, now_ms, username),
        )
        conn.commit()
    finally:
        conn.close()
    return get_user_access(username)


def add_user_access_days(username: str, days_delta: int) -> dict[str, Any] | None:
    row = get_user_access(username)
    if not row:
        return None

    if int(row["is_permanent"]) == 1:
        return row

    now_ms = _now_ms()
    current_expiry = int(row["expires_at_ms"] or now_ms)
    base = current_expiry if current_expiry > now_ms else now_ms
    expires_at_ms = base + days_delta * 86400000

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_access SET expires_at_ms = ?, updated_at_ms = ? WHERE username = ?",
            (expires_at_ms, now_ms, username),
        )
        conn.commit()
    finally:
        conn.close()
    return get_user_access(username)


def set_user_access_permanent(username: str, permanent: bool) -> dict[str, Any] | None:
    row = get_user_access(username)
    if not row:
        return None
    now_ms = _now_ms()
    expires = None if permanent else (row["expires_at_ms"] or now_ms + 30 * 86400000)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_access SET is_permanent = ?, expires_at_ms = ?, updated_at_ms = ? WHERE username = ?",
            (1 if permanent else 0, expires, now_ms, username),
        )
        conn.commit()
    finally:
        conn.close()
    return get_user_access(username)


def get_expired_usernames(now_ms: int | None = None) -> list[str]:
    ts = now_ms if now_ms is not None else _now_ms()
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT username
            FROM user_access
            WHERE is_permanent = 0
              AND expires_at_ms IS NOT NULL
              AND expires_at_ms < ?
            """,
            (ts,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_latest_username_by_tg_id(tg_id: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT username
            FROM subscriptions
            WHERE tg_id = ?
            ORDER BY created_at_ms DESC
            LIMIT 1
            """,
            (tg_id,),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
