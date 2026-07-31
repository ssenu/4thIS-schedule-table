"""카테고리 CRUD. 표의 배치를 바꾸는 조작이므로 전부 관리자 전용이다."""

import sqlite3

from fastapi import APIRouter, Depends, Response

from app.auth import Actor, require_admin, resolve_actor
from app.errors import Conflict, DomainError, NotFound
from app.routers.board import get_conn
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate, OrderIn

router = APIRouter(prefix="/api/categories")


def _fetch(conn: sqlite3.Connection, category_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, name, sort_order FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if row is None:
        raise NotFound("카테고리를 찾을 수 없습니다.")
    return row


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CategoryOut:
    require_admin(actor)
    try:
        cursor = conn.execute(
            "INSERT INTO categories (name, sort_order)"
            " VALUES (?, (SELECT COALESCE(MAX(sort_order) + 1, 0) FROM categories))",
            (payload.name,),
        )
    except sqlite3.IntegrityError as exc:
        raise Conflict("이미 있는 이름입니다.") from exc
    return CategoryOut(**dict(_fetch(conn, cursor.lastrowid)))


@router.patch("/{category_id}", response_model=CategoryOut)
def rename_category(
    category_id: int,
    payload: CategoryUpdate,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> CategoryOut:
    require_admin(actor)
    _fetch(conn, category_id)
    try:
        conn.execute(
            "UPDATE categories SET name = ? WHERE id = ?", (payload.name, category_id)
        )
    except sqlite3.IntegrityError as exc:
        raise Conflict("이미 있는 이름입니다.") from exc
    return CategoryOut(**dict(_fetch(conn, category_id)))


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    require_admin(actor)
    _fetch(conn, category_id)

    total = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    if total <= 1:
        raise Conflict("카테고리는 최소 1개 있어야 합니다.")

    occupants = conn.execute(
        "SELECT COUNT(*) AS n FROM members WHERE category_id = ?", (category_id,)
    ).fetchone()["n"]
    if occupants:
        raise Conflict(f"소속된 멤버 {occupants}명을 먼저 옮겨 주세요.")

    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    return Response(status_code=204)


@router.put("/order")
def reorder_categories(
    payload: OrderIn,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    require_admin(actor)
    existing = {row["id"] for row in conn.execute("SELECT id FROM categories")}
    if set(payload.ordered_ids) != existing:
        raise DomainError(
            "카테고리 목록이 서버와 다릅니다. 새로고침 후 다시 시도해 주세요."
        )
    conn.executemany(
        "UPDATE categories SET sort_order = ? WHERE id = ?",
        [(index, cid) for index, cid in enumerate(payload.ordered_ids)],
    )
    return {"ok": True}
