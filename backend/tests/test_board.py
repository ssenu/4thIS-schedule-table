from app.auth import hash_password
from app.constants import DEFAULT_CATEGORIES


def test_board_returns_seeded_categories(client):
    body = client.get("/api/board").json()
    assert [c["name"] for c in body["categories"]] == DEFAULT_CATEGORIES


def test_board_has_all_three_collections(client):
    body = client.get("/api/board").json()
    assert set(body) == {"categories", "members", "schedules"}


def test_board_is_empty_of_members_at_first(client):
    body = client.get("/api/board").json()
    assert body["members"] == []
    assert body["schedules"] == []


def test_board_lists_members_and_schedules(client, conn, make_member):
    member_id, _ = make_member("철수")
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 14, '전공수업', '#ef4444')",
        (member_id,),
    )
    body = client.get("/api/board").json()
    assert body["members"][0]["name"] == "철수"
    schedule = body["schedules"][0]
    assert (schedule["start_slot"], schedule["end_slot"]) == (6, 14)
    assert schedule["title"] == "전공수업"


def test_board_never_leaks_password_hash(client, make_member):
    make_member("철수")
    response = client.get("/api/board")
    assert "password_hash" not in response.json()["members"][0]
    assert "1234" not in response.text


def test_board_orders_by_sort_order(client, conn, category_id):
    for index, name in enumerate(["다", "가", "나"]):
        conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES (?, ?, ?, ?)",
            (name, category_id, hash_password("1234"), 2 - index),
        )
    body = client.get("/api/board").json()
    assert [m["name"] for m in body["members"]] == ["나", "가", "다"]
