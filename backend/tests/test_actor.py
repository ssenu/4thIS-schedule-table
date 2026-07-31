from urllib.parse import quote


def test_verify_accepts_admin(client, admin_headers):
    response = client.post(
        "/api/auth/verify", json={"scope": "admin"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_verify_rejects_wrong_admin_password(client):
    response = client.post(
        "/api/auth/verify",
        json={"scope": "admin"},
        headers={"X-Admin-Password": quote("틀린값", safe="")},
    )
    assert response.status_code == 401


def test_verify_accepts_member(client, make_member):
    member_id, headers = make_member("철수")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers=headers,
    )
    assert response.status_code == 200


def test_verify_rejects_wrong_member_password(client, make_member):
    member_id, _ = make_member("철수", password="1234")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers={"X-Member-Id": str(member_id), "X-Member-Password": "9999"},
    )
    assert response.status_code == 401


def test_failure_message_reports_remaining_attempts(client, make_member):
    member_id, _ = make_member("철수")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers={"X-Member-Id": str(member_id), "X-Member-Password": "9999"},
    )
    assert "9" in response.json()["detail"]


def test_lockout_after_ten_failures(client, make_member):
    member_id, _ = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    response = client.post("/api/auth/verify", json=body, headers=bad)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "601"


def test_lockout_blocks_even_the_correct_password(client, make_member):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    assert client.post("/api/auth/verify", json=body, headers=good).status_code == 429


def test_lockout_expires(client, make_member, clock):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    clock.advance(601)
    assert client.post("/api/auth/verify", json=body, headers=good).status_code == 200


def test_success_resets_the_counter(client, make_member):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(9):
        client.post("/api/auth/verify", json=body, headers=bad)
    client.post("/api/auth/verify", json=body, headers=good)
    response = client.post("/api/auth/verify", json=body, headers=bad)
    assert "9" in response.json()["detail"]


def test_verify_rejects_unknown_member(client):
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": 999},
        headers={"X-Member-Id": "999", "X-Member-Password": "1234"},
    )
    assert response.status_code == 401


def test_verify_member_scope_requires_matching_header(client, make_member):
    _, first_headers = make_member("철수")
    second_id, _ = make_member("영희")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": second_id},
        headers=first_headers,
    )
    assert response.status_code == 403


def test_non_ascii_admin_password_survives_the_header(client, conn, make_member):
    """한글 관리자 비밀번호도 통해야 한다. 헤더는 ASCII만 실을 수 있다."""
    from app.auth import hash_password
    from app.db import set_setting

    set_setting(conn, "admin_password_hash", hash_password("관리자비밀"))
    response = client.post(
        "/api/auth/verify",
        json={"scope": "admin"},
        headers={"X-Admin-Password": quote("관리자비밀", safe="")},
    )
    assert response.status_code == 200


def test_admin_header_wins_over_member_header(client, make_member, admin_headers):
    _, member_headers = make_member("철수")
    merged = {**member_headers, **admin_headers}
    response = client.post("/api/auth/verify", json={"scope": "admin"}, headers=merged)
    assert response.status_code == 200
