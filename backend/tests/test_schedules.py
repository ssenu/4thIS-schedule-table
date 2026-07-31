import pytest

from app.constants import PALETTE

COLOR = PALETTE[0]


def payload(member_id, **overrides):
    body = {
        "member_id": member_id,
        "day_of_week": 0,
        "start_slot": 6,
        "end_slot": 14,
        "title": "전공수업",
        "color": COLOR,
    }
    body.update(overrides)
    return body


def test_self_can_create(client, make_member):
    member_id, headers = make_member("철수")
    response = client.post("/api/schedules", json=payload(member_id), headers=headers)
    assert response.status_code == 201
    assert response.json()["title"] == "전공수업"


def test_anonymous_cannot_create(client, make_member):
    member_id, _ = make_member("철수")
    assert client.post("/api/schedules", json=payload(member_id)).status_code == 403


def test_other_member_cannot_create_for_someone_else(client, make_member):
    target_id, _ = make_member("철수")
    _, other_headers = make_member("영희")
    response = client.post(
        "/api/schedules", json=payload(target_id), headers=other_headers
    )
    assert response.status_code == 403


def test_admin_can_create_for_anyone(client, make_member, admin_headers):
    member_id, _ = make_member("철수")
    response = client.post(
        "/api/schedules", json=payload(member_id), headers=admin_headers
    )
    assert response.status_code == 201


def test_overlapping_schedule_is_rejected(client, make_member):
    member_id, headers = make_member("철수")
    client.post("/api/schedules", json=payload(member_id), headers=headers)
    response = client.post(
        "/api/schedules",
        json=payload(member_id, start_slot=10, end_slot=18, title="알바"),
        headers=headers,
    )
    assert response.status_code == 409
    assert "전공수업" in response.json()["detail"]
    assert "09:00~13:00" in response.json()["detail"]


def test_adjacent_schedules_are_allowed(client, make_member):
    member_id, headers = make_member("철수")
    client.post("/api/schedules", json=payload(member_id), headers=headers)
    response = client.post(
        "/api/schedules",
        json=payload(member_id, start_slot=14, end_slot=18, title="알바"),
        headers=headers,
    )
    assert response.status_code == 201


def test_same_time_on_another_day_is_allowed(client, make_member):
    member_id, headers = make_member("철수")
    client.post("/api/schedules", json=payload(member_id), headers=headers)
    response = client.post(
        "/api/schedules", json=payload(member_id, day_of_week=1), headers=headers
    )
    assert response.status_code == 201


def test_two_members_may_share_a_time(client, make_member):
    first_id, first_headers = make_member("철수")
    second_id, second_headers = make_member("영희")
    client.post("/api/schedules", json=payload(first_id), headers=first_headers)
    response = client.post(
        "/api/schedules", json=payload(second_id), headers=second_headers
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_slot": -1},
        {"start_slot": 36},
        {"end_slot": 0},
        {"end_slot": 37},
        {"day_of_week": 7},
        {"day_of_week": -1},
        {"title": ""},
        {"title": "가" * 31},
        {"color": "#123456"},
    ],
)
def test_invalid_payloads_are_rejected(client, make_member, overrides):
    member_id, headers = make_member("철수")
    response = client.post(
        "/api/schedules", json=payload(member_id, **overrides), headers=headers
    )
    assert response.status_code == 422


def test_reversed_range_is_rejected(client, make_member):
    member_id, headers = make_member("철수")
    response = client.post(
        "/api/schedules",
        json=payload(member_id, start_slot=14, end_slot=6),
        headers=headers,
    )
    assert response.status_code == 422


def test_full_day_schedule_is_allowed(client, make_member):
    member_id, headers = make_member("철수")
    response = client.post(
        "/api/schedules",
        json=payload(member_id, start_slot=0, end_slot=36),
        headers=headers,
    )
    assert response.status_code == 201


def test_update_changes_time(client, make_member):
    member_id, headers = make_member("철수")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    response = client.patch(
        f"/api/schedules/{created['id']}", json={"end_slot": 20}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["end_slot"] == 20


def test_update_excludes_itself_from_overlap_check(client, make_member):
    member_id, headers = make_member("철수")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    response = client.patch(
        f"/api/schedules/{created['id']}",
        json={"title": "이름만 변경"},
        headers=headers,
    )
    assert response.status_code == 200


def test_update_detects_overlap_with_others(client, make_member):
    member_id, headers = make_member("철수")
    first = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    client.post(
        "/api/schedules",
        json=payload(member_id, start_slot=20, end_slot=24, title="알바"),
        headers=headers,
    )
    response = client.patch(
        f"/api/schedules/{first['id']}", json={"end_slot": 22}, headers=headers
    )
    assert response.status_code == 409


def test_other_member_cannot_update(client, make_member):
    member_id, headers = make_member("철수")
    _, other_headers = make_member("영희")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    response = client.patch(
        f"/api/schedules/{created['id']}", json={"title": "해킹"}, headers=other_headers
    )
    assert response.status_code == 403


def test_self_can_delete(client, make_member):
    member_id, headers = make_member("철수")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    deleted = client.delete(f"/api/schedules/{created['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/board").json()["schedules"] == []


def test_other_member_cannot_delete(client, make_member):
    member_id, headers = make_member("철수")
    _, other_headers = make_member("영희")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    response = client.delete(f"/api/schedules/{created['id']}", headers=other_headers)
    assert response.status_code == 403


def test_admin_can_delete_anyones(client, make_member, admin_headers):
    member_id, headers = make_member("철수")
    created = client.post(
        "/api/schedules", json=payload(member_id), headers=headers
    ).json()
    response = client.delete(f"/api/schedules/{created['id']}", headers=admin_headers)
    assert response.status_code == 204


def test_unknown_schedule_returns_404(client, make_member):
    _, headers = make_member("철수")
    assert client.delete("/api/schedules/999", headers=headers).status_code == 404
