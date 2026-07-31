"""프론트의 잠금 해제 UI 전용 확인 엔드포인트."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import Actor, require_self_or_admin, resolve_actor
from app.errors import Unauthorized

router = APIRouter()


class VerifyIn(BaseModel):
    scope: Literal["admin", "member"]
    member_id: int | None = None


@router.post("/api/auth/verify")
def verify(payload: VerifyIn, actor: Actor = Depends(resolve_actor)) -> dict:
    if payload.scope == "admin":
        if not actor.is_admin:
            raise Unauthorized("관리자 비밀번호가 필요합니다.")
        return {"ok": True}

    if payload.member_id is None:
        raise Unauthorized("멤버를 지정해 주세요.")
    if actor.is_anonymous:
        raise Unauthorized("비밀번호가 필요합니다.")
    require_self_or_admin(actor, payload.member_id)
    return {"ok": True}
