"""입장 게이트 API.

문구 읽기와 비밀번호 확인은 게이트 밖에 있다 — 첫 화면을 그리려면 문구가
필요하고, 비밀번호는 어딘가에서 확인해야 하기 때문이다. 고치는 것은
관리자만 할 수 있고, 그 요청은 게이트 안쪽으로 지나간다.
"""

import sqlite3

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import Actor, LockedOut, client_key, require_admin, resolve_actor
from app.errors import TooManyAttempts, Unauthorized
from app.gate import (
    INTRO_MAX_LEN,
    MIN_GATE_PASSWORD_LEN,
    TITLE_MAX_LEN,
    read_gate,
    set_gate_password,
    write_gate,
)
from app.routers.board import get_conn

router = APIRouter(prefix="/api/gate")


class GateOut(BaseModel):
    title: str
    intro: str


class GateVerifyIn(BaseModel):
    password: str


class GateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LEN)
    intro: str | None = Field(default=None, max_length=INTRO_MAX_LEN)
    password: str | None = Field(default=None, min_length=MIN_GATE_PASSWORD_LEN)


@router.get("", response_model=GateOut)
def read(conn: sqlite3.Connection = Depends(get_conn)) -> GateOut:
    return GateOut(**read_gate(conn))


@router.post("/verify")
def verify(
    payload: GateVerifyIn,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """사람이 직접 입력하는 창구. 여기서만 실패를 센다."""
    limiter = request.app.state.limiter
    key = client_key(request, "gate")
    try:
        limiter.check(key)
    except LockedOut as exc:
        raise TooManyAttempts(
            f"시도 횟수를 초과했습니다. {exc.retry_after}초 후 다시 시도해 주세요.",
            retry_after=exc.retry_after,
        ) from exc

    if request.app.state.gate.check(conn, payload.password):
        limiter.record_success(key)
        return {"ok": True}

    remaining = limiter.record_failure(key)
    raise Unauthorized(f"비밀번호가 맞지 않습니다. (남은 시도 {remaining}회)")


@router.patch("", response_model=GateOut)
def update(
    payload: GateUpdate,
    request: Request,
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> GateOut:
    require_admin(actor)
    write_gate(conn, title=payload.title, intro=payload.intro)
    if payload.password is not None:
        set_gate_password(conn, payload.password)
        # 옛 비밀번호로 들어와 있던 사람도 다시 물어봐야 한다.
        request.app.state.gate.reset()
    return GateOut(**read_gate(conn))
