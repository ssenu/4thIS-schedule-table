def test_create_requires_admin(client):
    assert client.post("/api/categories", json={"name": "4학년"}).status_code == 403


def test_member_cannot_create(client, make_member):
    _, headers = make_member("철수")
    response = client.post("/api/categories", json={"name": "4학년"}, headers=headers)
    assert response.status_code == 403


def test_admin_creates_category(client, admin_headers):
    response = client.post(
        "/api/categories", json={"name": "4학년"}, headers=admin_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "4학년"


def test_created_category_goes_last(client, admin_headers):
    client.post("/api/categories", json={"name": "4학년"}, headers=admin_headers)
    names = [c["name"] for c in client.get("/api/board").json()["categories"]]
    assert names[-1] == "4학년"


def test_duplicate_name_conflicts(client, admin_headers):
    client.post("/api/categories", json={"name": "4학년"}, headers=admin_headers)
    response = client.post(
        "/api/categories", json={"name": "4학년"}, headers=admin_headers
    )
    assert response.status_code == 409


def test_rename_category(client, admin_headers, category_id):
    response = client.patch(
        f"/api/categories/{category_id}",
        json={"name": "신입생"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "신입생"


def test_rename_unknown_category(client, admin_headers):
    response = client.patch(
        "/api/categories/999", json={"name": "x"}, headers=admin_headers
    )
    assert response.status_code == 404


def test_delete_empty_category(client, admin_headers, conn):
    target = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.delete(f"/api/categories/{target}", headers=admin_headers)
    assert response.status_code == 204


def test_delete_rejects_category_with_members(
    client, admin_headers, category_id, make_member
):
    make_member("철수")
    response = client.delete(f"/api/categories/{category_id}", headers=admin_headers)
    assert response.status_code == 409
    assert "1" in response.json()["detail"]


def test_cannot_delete_the_last_category(client, admin_headers, conn):
    ids = [row["id"] for row in conn.execute("SELECT id FROM categories")]
    for category in ids[:-1]:
        client.delete(f"/api/categories/{category}", headers=admin_headers)
    response = client.delete(f"/api/categories/{ids[-1]}", headers=admin_headers)
    assert response.status_code == 409


def test_reorder_categories(client, admin_headers, conn):
    rows = conn.execute("SELECT id FROM categories ORDER BY sort_order")
    ids = [row["id"] for row in rows]
    reversed_ids = list(reversed(ids))
    response = client.put(
        "/api/categories/order",
        json={"ordered_ids": reversed_ids},
        headers=admin_headers,
    )
    assert response.status_code == 200
    after = [c["id"] for c in client.get("/api/board").json()["categories"]]
    assert after == reversed_ids


def test_reorder_rejects_incomplete_list(client, admin_headers, conn):
    rows = conn.execute("SELECT id FROM categories ORDER BY sort_order")
    ids = [row["id"] for row in rows]
    response = client.put(
        "/api/categories/order", json={"ordered_ids": ids[:1]}, headers=admin_headers
    )
    assert response.status_code == 400


def test_reorder_requires_admin(client, conn):
    ids = [row["id"] for row in conn.execute("SELECT id FROM categories")]
    response = client.put("/api/categories/order", json={"ordered_ids": ids})
    assert response.status_code == 403


def test_blank_name_is_rejected(client, admin_headers):
    response = client.post("/api/categories", json={"name": ""}, headers=admin_headers)
    assert response.status_code == 422
