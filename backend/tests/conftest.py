from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.auth import AttemptLimiter, hash_password
from app.db import connect, initialize
from app.gate import GateKeeper, seed_gate
from app.main import create_app

ADMIN_PASSWORD = "admin-secret"
GATE_PASSWORD = "club-gate"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, hash_password(ADMIN_PASSWORD))
    seed_gate(connection, GATE_PASSWORD)
    yield connection
    connection.close()


@pytest.fixture
def limiter(clock):
    return AttemptLimiter(max_attempts=10, lockout_seconds=600, clock=clock)


@pytest.fixture
def keeper():
    return GateKeeper()


@pytest.fixture
def app(conn, limiter, keeper):
    return create_app(conn, limiter, keeper)


@pytest.fixture
def client(app):
    """게이트를 통과한 손님. 모든 요청에 입장 비밀번호가 붙는다."""
    with TestClient(app) as test_client:
        test_client.headers.update(
            {"X-Gate-Password": quote(GATE_PASSWORD, safe="")}
        )
        yield test_client


@pytest.fixture
def stranger(app):
    """입장 비밀번호를 모르는 손님."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers():
    return {"X-Admin-Password": ADMIN_PASSWORD}


@pytest.fixture
def category_id(conn):
    return conn.execute(
        "SELECT id FROM categories ORDER BY sort_order"
    ).fetchone()["id"]


@pytest.fixture
def make_member(conn, category_id):
    """(id, headers)를 돌려주는 헬퍼. headers는 그 멤버 자격의 인증 헤더다."""

    def _make(
        name: str, password: str = "1234", cat_id: int | None = None
    ) -> tuple[int, dict]:
        target = cat_id or category_id
        cursor = conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES (?, ?, ?,"
            "   (SELECT COALESCE(MAX(sort_order) + 1, 0) FROM members"
            "    WHERE category_id = ?))",
            (name, target, hash_password(password), target),
        )
        member_id = cursor.lastrowid
        headers = {"X-Member-Id": str(member_id), "X-Member-Password": password}
        return member_id, headers

    return _make
