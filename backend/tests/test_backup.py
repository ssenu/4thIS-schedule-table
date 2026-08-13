import sqlite3

SQLITE_MAGIC = b"SQLite format 3\x00"


def test_admin_downloads_a_real_sqlite_file(client, admin_headers, make_member):
    make_member("철수")
    response = client.get("/api/backup", headers=admin_headers)
    assert response.status_code == 200
    assert response.content[: len(SQLITE_MAGIC)] == SQLITE_MAGIC


def test_backup_carries_the_data_and_the_hashes(
    client, admin_headers, make_member, tmp_path
):
    """이름과 일정뿐 아니라 비밀번호 해시까지 옮겨져야 한다.

    해시가 빠지면 옮긴 자리에서 동아리원 모두가 비밀번호를 다시 만들어야 한다.
    """
    member_id, _ = make_member("철수")
    client.post(
        "/api/schedules",
        json={
            "member_id": member_id,
            "day_of_week": 2,
            "start_slot": 6,
            "end_slot": 10,
            "title": "전공수업",
            "color": "#a9dcb5",
        },
        headers=admin_headers,
    )

    copy = tmp_path / "copy.db"
    copy.write_bytes(client.get("/api/backup", headers=admin_headers).content)

    taken = sqlite3.connect(copy)
    names = [row[0] for row in taken.execute("SELECT name FROM members")]
    titles = [row[0] for row in taken.execute("SELECT title FROM schedules")]
    hashes = [row[0] for row in taken.execute("SELECT password_hash FROM members")]
    assert names == ["철수"]
    assert titles == ["전공수업"]
    assert hashes[0].startswith("$2b$")


def test_backup_keeps_the_gate_settings(client, admin_headers, tmp_path):
    """첫 화면 문구와 입장 비밀번호도 함께 간다.

    비밀번호는 바꾸지 않고 심어진 것을 그대로 본다 — 여기서 바꾸면 이 손님이
    들고 있는 입장 비밀번호가 그 순간 옛것이 되어 다음 요청부터 막힌다.
    """
    client.patch(
        "/api/gate", json={"title": "4thIS 시간표"}, headers=admin_headers
    )
    copy = tmp_path / "copy.db"
    copy.write_bytes(client.get("/api/backup", headers=admin_headers).content)

    taken = sqlite3.connect(copy)
    kept = dict(taken.execute("SELECT key, value FROM settings"))
    assert kept["gate_title"] == "4thIS 시간표"
    assert kept["gate_password_hash"].startswith("$2b$")


def test_member_cannot_download_backup(client, make_member):
    _, headers = make_member("철수")
    assert client.get("/api/backup", headers=headers).status_code == 403


def test_anonymous_cannot_download_backup(client):
    assert client.get("/api/backup").status_code == 403


def test_backup_needs_the_entry_password(stranger, admin_headers):
    assert stranger.get("/api/backup", headers=admin_headers).status_code == 401
