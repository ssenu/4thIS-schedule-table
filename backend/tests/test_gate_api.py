from urllib.parse import quote

from app.gate import DEFAULT_INTRO, DEFAULT_TITLE
from tests.conftest import GATE_PASSWORD


def gate_headers(password: str) -> dict:
    return {"X-Gate-Password": quote(password, safe="")}


def test_read_returns_the_default_text(stranger):
    assert stranger.get("/api/gate").json() == {
        "title": DEFAULT_TITLE,
        "intro": DEFAULT_INTRO,
    }


def test_verify_accepts_the_right_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_verify_refuses_a_wrong_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": "nope"})
    assert response.status_code == 401


def test_verify_counts_down_the_remaining_tries(stranger):
    response = stranger.post("/api/gate/verify", json={"password": "nope"})
    assert "9" in response.json()["detail"]


def test_verify_locks_out_after_ten_tries(stranger):
    for _ in range(10):
        stranger.post("/api/gate/verify", json={"password": "nope"})
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 429


def test_lockout_expires(stranger, clock):
    for _ in range(10):
        stranger.post("/api/gate/verify", json={"password": "nope"})
    clock.advance(601)
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200


def test_only_an_admin_may_change_the_gate(client):
    assert client.patch("/api/gate", json={"title": "몰래"}).status_code == 403


def test_a_member_may_not_change_the_gate(client, make_member):
    _, headers = make_member("철수")
    response = client.patch("/api/gate", json={"title": "몰래"}, headers=headers)
    assert response.status_code == 403


def test_admin_changes_the_text(client, admin_headers, stranger):
    response = client.patch(
        "/api/gate",
        json={"title": "4thIS 시간표", "intro": "문 앞에서 물어봅니다."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert stranger.get("/api/gate").json() == {
        "title": "4thIS 시간표",
        "intro": "문 앞에서 물어봅니다.",
    }


def test_admin_changes_the_password(client, admin_headers, stranger):
    client.patch("/api/gate", json={"password": "new-gate-word"}, headers=admin_headers)

    # 옛 비밀번호로는 더 못 들어온다 — 기억도 함께 지워져야 한다.
    assert stranger.get("/api/board", headers=gate_headers(GATE_PASSWORD)).status_code == 401
    assert stranger.get("/api/board", headers=gate_headers("new-gate-word")).status_code == 200


def test_a_blank_title_is_refused(client, admin_headers):
    response = client.patch("/api/gate", json={"title": ""}, headers=admin_headers)
    assert response.status_code == 422


def test_a_short_password_is_refused(client, admin_headers):
    response = client.patch("/api/gate", json={"password": "abc"}, headers=admin_headers)
    assert response.status_code == 422


def test_a_long_title_is_refused(client, admin_headers):
    response = client.patch(
        "/api/gate", json={"title": "가" * 41}, headers=admin_headers
    )
    assert response.status_code == 422


def test_the_intro_may_be_emptied(client, admin_headers, stranger):
    client.patch("/api/gate", json={"intro": ""}, headers=admin_headers)
    assert stranger.get("/api/gate").json()["intro"] == ""
