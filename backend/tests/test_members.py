def test_anyone_can_register(client, category_id):
    response = client.post(
        "/api/members",
        json={"name": "철수", "category_id": category_id, "password": "1234"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "철수"


def test_registration_never_returns_the_password(client, category_id):
    response = client.post(
        "/api/members",
        json={"name": "철수", "category_id": category_id, "password": "1234"},
    )
    assert "password" not in response.text


def test_password_must_be_four_digits(client, category_id):
    for bad in ["123", "12345", "abcd", ""]:
        response = client.post(
            "/api/members",
            json={"name": f"이름{bad}", "category_id": category_id, "password": bad},
        )
        assert response.status_code == 422, bad


def test_duplicate_name_conflicts(client, category_id):
    body = {"name": "철수", "category_id": category_id, "password": "1234"}
    client.post("/api/members", json=body)
    assert client.post("/api/members", json=body).status_code == 409


def test_unknown_category_is_rejected(client):
    response = client.post(
        "/api/members", json={"name": "철수", "category_id": 999, "password": "1234"}
    )
    assert response.status_code == 404


def test_self_can_rename(client, make_member):
    member_id, headers = make_member("철수")
    response = client.patch(
        f"/api/members/{member_id}", json={"name": "철수2"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "철수2"


def test_admin_can_rename_anyone(client, make_member, admin_headers):
    member_id, _ = make_member("철수")
    response = client.patch(
        f"/api/members/{member_id}", json={"name": "철수2"}, headers=admin_headers
    )
    assert response.status_code == 200


def test_other_member_cannot_rename(client, make_member):
    target_id, _ = make_member("철수")
    _, other_headers = make_member("영희")
    response = client.patch(
        f"/api/members/{target_id}", json={"name": "해킹"}, headers=other_headers
    )
    assert response.status_code == 403


def test_anonymous_cannot_rename(client, make_member):
    member_id, _ = make_member("철수")
    response = client.patch(f"/api/members/{member_id}", json={"name": "x"})
    assert response.status_code == 403


def test_self_can_change_password(client, make_member):
    member_id, headers = make_member("철수", password="1234")
    changed = client.patch(
        f"/api/members/{member_id}", json={"password": "5678"}, headers=headers
    )
    assert changed.status_code == 200
    new_headers = {"X-Member-Id": str(member_id), "X-Member-Password": "5678"}
    again = client.patch(
        f"/api/members/{member_id}", json={"name": "철수3"}, headers=new_headers
    )
    assert again.status_code == 200


def test_self_cannot_move_category(client, make_member, conn):
    member_id, headers = make_member("철수")
    other = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.patch(
        f"/api/members/{member_id}", json={"category_id": other}, headers=headers
    )
    assert response.status_code == 403
    assert "관리자" in response.json()["detail"]


def test_admin_can_move_category(client, make_member, admin_headers, conn):
    member_id, _ = make_member("철수")
    other = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.patch(
        f"/api/members/{member_id}", json={"category_id": other}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["category_id"] == other


def test_self_can_delete_own_account(client, make_member):
    member_id, headers = make_member("철수")
    deleted = client.delete(f"/api/members/{member_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/board").json()["members"] == []


def test_deleting_member_removes_schedules(client, make_member, conn):
    member_id, headers = make_member("철수")
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 9, '수업', '#ef4444')",
        (member_id,),
    )
    client.delete(f"/api/members/{member_id}", headers=headers)
    assert client.get("/api/board").json()["schedules"] == []


def test_other_member_cannot_delete(client, make_member):
    target_id, _ = make_member("철수")
    _, other_headers = make_member("영희")
    response = client.delete(f"/api/members/{target_id}", headers=other_headers)
    assert response.status_code == 403


def test_admin_reorders_members(client, make_member, admin_headers, category_id):
    first_id, _ = make_member("가")
    second_id, _ = make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [second_id, first_id]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    order = [m["id"] for m in client.get("/api/board").json()["members"]]
    assert order == [second_id, first_id]


def test_member_cannot_reorder(client, make_member, category_id):
    first_id, headers = make_member("가")
    second_id, _ = make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [second_id, first_id]},
        headers=headers,
    )
    assert response.status_code == 403


def test_reorder_rejects_mismatched_ids(
    client, make_member, admin_headers, category_id
):
    first_id, _ = make_member("가")
    make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [first_id]},
        headers=admin_headers,
    )
    assert response.status_code == 400
