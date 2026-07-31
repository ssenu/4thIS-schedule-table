"""SQLite 커넥션과 스키마. 날짜 컬럼은 어디에도 없다 — 시간표는 반복되는 한 주다."""

import sqlite3
from pathlib import Path

from app.constants import DEFAULT_CATEGORIES

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    category_id   INTEGER NOT NULL REFERENCES categories(id),
    password_hash TEXT    NOT NULL,
    sort_order    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id   INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_slot  INTEGER NOT NULL CHECK (start_slot BETWEEN 0 AND 35),
    end_slot    INTEGER NOT NULL CHECK (end_slot   BETWEEN 1 AND 36),
    title       TEXT    NOT NULL,
    color       TEXT    NOT NULL,
    CHECK (start_slot < end_slot)
);

CREATE INDEX IF NOT EXISTS idx_schedules_member_day
    ON schedules(member_id, day_of_week);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """커넥션을 연다. 행은 이름으로 접근하고, 외래키 제약을 켠다."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(conn: sqlite3.Connection, admin_password_hash: str) -> None:
    """스키마를 만들고 기본 카테고리를 시드한다. 여러 번 불러도 안전하다."""
    conn.executescript(SCHEMA)
    existing = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    if existing == 0:
        conn.executemany(
            "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
            [(name, index) for index, name in enumerate(DEFAULT_CATEGORIES)],
        )
    set_setting(conn, "admin_password_hash", admin_password_hash)


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
