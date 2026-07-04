from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pymysql


BASE_DIR = Path(__file__).resolve().parents[1]


def load_env_file() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

DB_CONFIG = {
    "host": os.getenv("TRAVEL_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("TRAVEL_DB_PORT", "3306")),
    "user": os.getenv("TRAVEL_DB_USER", "root"),
    "password": os.getenv("TRAVEL_DB_PASSWORD", ""),
    "database": os.getenv("TRAVEL_DB_NAME", "travel_ctrip"),
    "charset": os.getenv("TRAVEL_DB_CHARSET", "utf8mb4"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


@contextmanager
def get_conn():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def query_all(sql: str, params: Iterable[Any] | None = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params or ()))
            return list(cur.fetchall())


def query_one(sql: str, params: Iterable[Any] | None = None) -> Dict[str, Any] | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None


def parse_json_field(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return text
    try:
        return json.loads(text)
    except Exception:
        return text
