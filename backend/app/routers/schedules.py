"""일정 CRUD. 매주 반복되는 일정만 다루므로 날짜 필드가 없다."""

import sqlite3

from fastapi import APIRouter, Depends, Response

from app.auth import Actor, require_self_or_admin, resolve_actor
from app.errors import Conflict, DomainError, NotFound
from app.routers.board import get_conn
from app.schemas import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.timeslot import describe, overlaps

router = APIRouter(prefix="/api/schedules")

_FIELDS = ("day_of_week", "start_slot", "end_slot", "title", "color")


def _fetch(conn: sqlite3.Connection, schedule_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, member_id, day_of_week, start_slot, end_slot, title, color"
        " FROM schedules WHERE id = ?",
        (schedule_id,),
    ).fetchone()
    if row is None:
        raise NotFound("일정을 찾을 수 없습니다.")
    return row


def _guard_overlap(
    conn: sqlite3.Connection,
    member_id: int,
    day_of_week: int,
    start_slot: int,
    end_slot: int,
    exclude_id: int | None = None,
) -> None:
    """같은 사람 같은 요일에 이미 있는 일정과 겹치면 거부한다."""
    rows = conn.execute(
        "SELECT id, day_of_week, start_slot, end_slot, title FROM schedules"
        " WHERE member_id = ? AND day_of_week = ?",
        (member_id, day_of_week),
    ).fetchall()
    for row in rows:
        if row["id"] == exclude_id:
            continue
        if overlaps(start_slot, end_slot, row["start_slot"], row["end_slot"]):
            when = describe(row["day_of_week"], row["start_slot"], row["end_slot"])
            raise Conflict(f"{when} '{row['title']}'과(와) 겹칩니다.")


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(
    payload: ScheduleCreate,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ScheduleOut:
    member = conn.execute(
        "SELECT id FROM members WHERE id = ?", (payload.member_id,)
    ).fetchone()
    if member is None:
        raise NotFound("멤버를 찾을 수 없습니다.")
    require_self_or_admin(actor, payload.member_id)
    _guard_overlap(
        conn,
        payload.member_id,
        payload.day_of_week,
        payload.start_slot,
        payload.end_slot,
    )
    cursor = conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            payload.member_id,
            payload.day_of_week,
            payload.start_slot,
            payload.end_slot,
            payload.title,
            payload.color,
        ),
    )
    return ScheduleOut(**dict(_fetch(conn, cursor.lastrowid)))


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ScheduleOut:
    current = _fetch(conn, schedule_id)
    require_self_or_admin(actor, current["member_id"])

    merged = {}
    for field in _FIELDS:
        value = getattr(payload, field)
        merged[field] = current[field] if value is None else value

    if merged["start_slot"] >= merged["end_slot"]:
        raise DomainError("종료 시간은 시작 시간보다 뒤여야 합니다.")

    _guard_overlap(
        conn,
        current["member_id"],
        merged["day_of_week"],
        merged["start_slot"],
        merged["end_slot"],
        exclude_id=schedule_id,
    )
    conn.execute(
        "UPDATE schedules SET day_of_week = ?, start_slot = ?, end_slot = ?,"
        " title = ?, color = ? WHERE id = ?",
        (
            merged["day_of_week"],
            merged["start_slot"],
            merged["end_slot"],
            merged["title"],
            merged["color"],
            schedule_id,
        ),
    )
    return ScheduleOut(**dict(_fetch(conn, schedule_id)))


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    current = _fetch(conn, schedule_id)
    require_self_or_admin(actor, current["member_id"])
    conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    return Response(status_code=204)
