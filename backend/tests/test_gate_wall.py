from urllib.parse import quote

from tests.conftest import GATE_PASSWORD


def test_stranger_cannot_read_the_board(stranger):
    response = stranger.get("/api/board")
    assert response.status_code == 401
    assert response.headers["X-Gate"] == "required"


def test_stranger_cannot_register_a_member(stranger, category_id):
    response = stranger.post(
        "/api/members",
        json={"name": "몰래", "category_id": category_id, "password": "1234"},
    )
    assert response.status_code == 401


def test_a_wrong_gate_password_is_refused(stranger):
    response = stranger.get(
        "/api/board", headers={"X-Gate-Password": quote("틀린값", safe="")}
    )
    assert response.status_code == 401
    assert response.headers["X-Gate"] == "required"


def test_the_right_gate_password_opens_the_api(client):
    assert client.get("/api/board").status_code == 200


def test_gate_text_is_readable_without_the_password(stranger):
    response = stranger.get("/api/gate")
    assert response.status_code == 200
    assert "title" in response.json()


def test_verify_is_reachable_without_the_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200


def test_a_refused_request_does_not_count_toward_the_lockout(stranger, limiter):
    """비밀번호가 바뀐 걸 모르고 폴링하던 사람이 잠기면 안 된다."""
    for _ in range(30):
        stranger.get("/api/board")

    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200
