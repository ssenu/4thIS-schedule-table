"""전체 시간표를 한 번에 내려주는 읽기 전용 엔드포인트."""

import sqlite3

from fastapi import APIRouter, Depends, Request

from app.schemas import BoardOut, CategoryOut, MemberOut, ScheduleOut

router = APIRouter()


def get_conn(request: Request) -> sqlite3.Connection:
    return request.app.state.conn


@router.get("/api/board", response_model=BoardOut)
def get_board(conn: sqlite3.Connection = Depends(get_conn)) -> BoardOut:
    categories = conn.execute(
        "SELECT id, name, sort_order FROM categories ORDER BY sort_order, id"
    ).fetchall()
    members = conn.execute(
        "SELECT id, name, category_id, sort_order FROM members"
        " ORDER BY sort_order, id"
    ).fetchall()
    schedules = conn.execute(
        "SELECT id, member_id, day_of_week, start_slot, end_slot, title, color"
        " FROM schedules ORDER BY day_of_week, start_slot, id"
    ).fetchall()
    return BoardOut(
        categories=[CategoryOut(**dict(row)) for row in categories],
        members=[MemberOut(**dict(row)) for row in members],
        schedules=[ScheduleOut(**dict(row)) for row in schedules],
    )
