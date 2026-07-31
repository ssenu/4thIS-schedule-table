import sqlite3

import pytest

from app.constants import DEFAULT_CATEGORIES
from app.db import connect, get_setting, initialize


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, "hashed-admin")
    yield connection
    connection.close()


def test_tables_exist(conn):
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"categories", "members", "schedules", "settings"} <= names


def test_default_categories_are_seeded(conn):
    rows = conn.execute("SELECT name FROM categories ORDER BY sort_order").fetchall()
    assert [row["name"] for row in rows] == DEFAULT_CATEGORIES


def test_admin_hash_is_stored(conn):
    assert get_setting(conn, "admin_password_hash") == "hashed-admin"


def test_initialize_is_idempotent(conn):
    initialize(conn, "hashed-admin")
    count = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    assert count == len(DEFAULT_CATEGORIES)


def test_initialize_updates_admin_hash(conn):
    initialize(conn, "new-hash")
    assert get_setting(conn, "admin_password_hash") == "new-hash"


def test_rows_are_dict_like(conn):
    row = conn.execute("SELECT id, name FROM categories LIMIT 1").fetchone()
    assert row["name"] == DEFAULT_CATEGORIES[0]


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES ('없는사람', 999, 'x', 0)"
        )


def test_deleting_member_cascades_to_schedules(conn):
    category_id = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()["id"]
    cursor = conn.execute(
        "INSERT INTO members (name, category_id, password_hash, sort_order)"
        " VALUES ('철수', ?, 'x', 0)",
        (category_id,),
    )
    member_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 9, '전공수업', '#ef4444')",
        (member_id,),
    )
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    remaining = conn.execute("SELECT COUNT(*) AS n FROM schedules").fetchone()["n"]
    assert remaining == 0


def test_schedule_rejects_reversed_range(conn):
    category_id = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()["id"]
    cursor = conn.execute(
        "INSERT INTO members (name, category_id, password_hash, sort_order)"
        " VALUES ('영희', ?, 'x', 0)",
        (category_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO schedules"
            " (member_id, day_of_week, start_slot, end_slot, title, color)"
            " VALUES (?, 0, 10, 6, '거꾸로', '#ef4444')",
            (cursor.lastrowid,),
        )
