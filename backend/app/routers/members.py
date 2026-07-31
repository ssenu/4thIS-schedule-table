"""멤버 CRUD. PATCH는 필드마다 필요한 권한이 다르다."""

import sqlite3

from fastapi import APIRouter, Depends, Response

from app.auth import (
    Actor,
    hash_password,
    require_admin,
    require_self_or_admin,
    resolve_actor,
)
from app.errors import Conflict, DomainError, Forbidden, NotFound
from app.routers.board import get_conn
from app.schemas import MemberCreate, MemberOrderIn, MemberOut, MemberUpdate

router = APIRouter(prefix="/api/members")

_NEXT_ORDER = (
    "(SELECT COALESCE(MAX(sort_order) + 1, 0) FROM members WHERE category_id = ?)"
)


def _fetch(conn: sqlite3.Connection, member_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, name, category_id, sort_order FROM members WHERE id = ?",
        (member_id,),
    ).fetchone()
    if row is None:
        raise NotFound("멤버를 찾을 수 없습니다.")
    return row


def _require_category(conn: sqlite3.Connection, category_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if row is None:
        raise NotFound("카테고리를 찾을 수 없습니다.")


@router.post("", response_model=MemberOut, status_code=201)
def create_member(
    payload: MemberCreate,
    conn: sqlite3.Connection = Depends(get_conn),
) -> MemberOut:
    """등록은 익명 허용. 본인이 여기서 4자리 비밀번호를 정한다."""
    _require_category(conn, payload.category_id)
    try:
        cursor = conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            f" VALUES (?, ?, ?, {_NEXT_ORDER})",
            (
                payload.name,
                payload.category_id,
                hash_password(payload.password),
                payload.category_id,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise Conflict("이미 있는 이름입니다.") from exc
    return MemberOut(**dict(_fetch(conn, cursor.lastrowid)))


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> MemberOut:
    _fetch(conn, member_id)
    require_self_or_admin(actor, member_id)

    if payload.category_id is not None and not actor.is_admin:
        raise Forbidden("소속 변경은 관리자에게 요청해 주세요.")

    if payload.name is not None:
        try:
            conn.execute(
                "UPDATE members SET name = ? WHERE id = ?", (payload.name, member_id)
            )
        except sqlite3.IntegrityError as exc:
            raise Conflict("이미 있는 이름입니다.") from exc

    if payload.password is not None:
        conn.execute(
            "UPDATE members SET password_hash = ? WHERE id = ?",
            (hash_password(payload.password), member_id),
        )

    if payload.category_id is not None:
        _require_category(conn, payload.category_id)
        conn.execute(
            f"UPDATE members SET category_id = ?, sort_order = {_NEXT_ORDER}"
            " WHERE id = ?",
            (payload.category_id, payload.category_id, member_id),
        )

    return MemberOut(**dict(_fetch(conn, member_id)))


@router.delete("/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    _fetch(conn, member_id)
    require_self_or_admin(actor, member_id)
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    return Response(status_code=204)


@router.put("/order")
def reorder_members(
    payload: MemberOrderIn,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """이름 순서는 표의 배치라서 관리자 전용이다."""
    require_admin(actor)
    _require_category(conn, payload.category_id)
    rows = conn.execute(
        "SELECT id FROM members WHERE category_id = ?", (payload.category_id,)
    )
    existing = {row["id"] for row in rows}
    if set(payload.ordered_ids) != existing:
        raise DomainError("멤버 목록이 서버와 다릅니다. 새로고침 후 다시 시도해 주세요.")
    conn.executemany(
        "UPDATE members SET sort_order = ? WHERE id = ?",
        [(index, mid) for index, mid in enumerate(payload.ordered_ids)],
    )
    return {"ok": True}
