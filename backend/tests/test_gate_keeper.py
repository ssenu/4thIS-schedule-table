import pytest

from app.auth import hash_password
from app.db import connect, get_setting, initialize
from app.gate import (
    DEFAULT_INTRO,
    DEFAULT_TITLE,
    GATE_HASH_KEY,
    GateKeeper,
    read_gate,
    seed_gate,
    set_gate_password,
    write_gate,
)


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, hash_password("admin"))
    yield connection
    connection.close()


def test_seed_sets_password_and_text(conn):
    seed_gate(conn, "club-gate")
    assert get_setting(conn, GATE_HASH_KEY) is not None
    assert read_gate(conn) == {"title": DEFAULT_TITLE, "intro": DEFAULT_INTRO}


def test_seed_does_not_overwrite_an_existing_password(conn):
    """관리자가 사이트에서 바꾼 비밀번호가 재시작 때 되돌아가면 안 된다."""
    seed_gate(conn, "first")
    set_gate_password(conn, "changed-by-admin")
    seed_gate(conn, "first")

    keeper = GateKeeper()
    assert keeper.check(conn, "changed-by-admin") is True
    assert keeper.check(conn, "first") is False


def test_keeper_accepts_the_right_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "club-gate") is True


def test_keeper_rejects_a_wrong_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "nope") is False


def test_keeper_rejects_an_empty_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "") is False


def test_keeper_remembers_and_skips_the_slow_check(conn):
    """두 번째부터는 저장된 해시를 지워도 통과한다 — 기억으로 답했다는 뜻이다."""
    seed_gate(conn, "club-gate")
    keeper = GateKeeper()
    assert keeper.check(conn, "club-gate") is True

    conn.execute("DELETE FROM settings WHERE key = ?", (GATE_HASH_KEY,))
    assert keeper.check(conn, "club-gate") is True


def test_reset_forgets_everything(conn):
    seed_gate(conn, "club-gate")
    keeper = GateKeeper()
    keeper.check(conn, "club-gate")
    keeper.reset()

    conn.execute("DELETE FROM settings WHERE key = ?", (GATE_HASH_KEY,))
    assert keeper.check(conn, "club-gate") is False


def test_write_gate_changes_only_what_is_given(conn):
    seed_gate(conn, "club-gate")
    write_gate(conn, title="4thIS 시간표")
    assert read_gate(conn) == {"title": "4thIS 시간표", "intro": DEFAULT_INTRO}

    write_gate(conn, intro="문 앞에서 물어봅니다.")
    assert read_gate(conn) == {
        "title": "4thIS 시간표",
        "intro": "문 앞에서 물어봅니다.",
    }


def test_intro_can_be_emptied(conn):
    seed_gate(conn, "club-gate")
    write_gate(conn, intro="")
    assert read_gate(conn)["intro"] == ""
