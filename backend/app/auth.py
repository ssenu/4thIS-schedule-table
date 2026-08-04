"""비밀번호 해시, 무차별 대입 방어, 요청 주체 판정.

4자리 숫자는 경우의 수가 10,000개뿐이라 시도 제한이 없으면 금방 뚫린다.
카운터는 프로세스 메모리에 있으므로 uvicorn 워커는 1개로 배포해야 한다.
"""

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import unquote

import bcrypt
from fastapi import Request

from app.constants import LOCKOUT_SECONDS, MAX_FAILED_ATTEMPTS
from app.db import get_setting
from app.errors import Forbidden, TooManyAttempts, Unauthorized


class LockedOut(Exception):
    """시도 횟수를 초과해 잠긴 상태."""

    def __init__(self, retry_after: int):
        super().__init__(f"{retry_after}초 후 다시 시도해 주세요.")
        self.retry_after = retry_after


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


@dataclass
class _Entry:
    failures: int = 0
    locked_until: float = 0.0


@dataclass
class AttemptLimiter:
    max_attempts: int = MAX_FAILED_ATTEMPTS
    lockout_seconds: int = LOCKOUT_SECONDS
    clock: Callable[[], float] = time.monotonic
    _entries: dict[str, _Entry] = field(default_factory=dict)

    def check(self, key: str) -> None:
        """잠겨 있으면 LockedOut을 던진다. 비밀번호를 대조하기 전에 부른다."""
        entry = self._entries.get(key)
        if entry is None:
            return
        remaining = entry.locked_until - self.clock()
        if remaining > 0:
            raise LockedOut(retry_after=int(remaining) + 1)
        if entry.locked_until:
            self._entries.pop(key, None)

    def record_failure(self, key: str) -> int:
        """실패를 기록하고 남은 시도 횟수를 돌려준다."""
        entry = self._entries.setdefault(key, _Entry())
        entry.failures += 1
        remaining = self.max_attempts - entry.failures
        if remaining <= 0:
            entry.locked_until = self.clock() + self.lockout_seconds
            return 0
        return remaining

    def record_success(self, key: str) -> None:
        self._entries.pop(key, None)


@dataclass(frozen=True)
class Actor:
    """요청을 보낸 주체. 익명이면 둘 다 비어 있다."""

    is_admin: bool = False
    member_id: int | None = None

    @property
    def is_anonymous(self) -> bool:
        return not self.is_admin and self.member_id is None


def read_password_header(request: Request, name: str) -> str | None:
    """비밀번호 헤더를 읽어 퍼센트 디코딩한다.

    HTTP 헤더 값은 ASCII만 안전하다. 관리자 비밀번호는 길이·문자 제한이 없어
    한글이 들어갈 수 있으므로, 클라이언트가 encodeURIComponent로 감싸 보내고
    여기서 푼다.
    """
    raw = request.headers.get(name)
    return None if raw is None else unquote(raw)


def client_key(request: Request, target: str) -> str:
    """시도 제한을 세는 단위. 같은 곳에서 같은 대상을 두드린 횟수를 센다."""
    host = request.client.host if request.client else "unknown"
    return f"{host}:{target}"


def _check_password(
    request: Request, target: str, raw: str, hashed: str | None
) -> bool:
    """시도 제한을 적용하며 비밀번호를 대조한다. 실패하면 예외를 던진다."""
    limiter: AttemptLimiter = request.app.state.limiter
    key = client_key(request, target)
    try:
        limiter.check(key)
    except LockedOut as exc:
        raise TooManyAttempts(
            f"시도 횟수를 초과했습니다. {exc.retry_after}초 후 다시 시도해 주세요.",
            retry_after=exc.retry_after,
        ) from exc
    if hashed is not None and verify_password(raw, hashed):
        limiter.record_success(key)
        return True
    remaining = limiter.record_failure(key)
    raise Unauthorized(f"비밀번호가 틀렸습니다. (남은 시도 {remaining}회)")


def resolve_actor(request: Request) -> Actor:
    """헤더에서 행위자를 판정한다. 관리자 헤더가 있으면 그쪽이 우선한다."""
    conn: sqlite3.Connection = request.app.state.conn

    admin_password = read_password_header(request, "X-Admin-Password")
    if admin_password:
        _check_password(
            request,
            "admin",
            admin_password,
            get_setting(conn, "admin_password_hash"),
        )
        return Actor(is_admin=True)

    member_id_header = request.headers.get("X-Member-Id")
    member_password = read_password_header(request, "X-Member-Password")
    if member_id_header and member_password:
        try:
            member_id = int(member_id_header)
        except ValueError as exc:
            raise Unauthorized("멤버 정보가 올바르지 않습니다.") from exc
        row = conn.execute(
            "SELECT password_hash FROM members WHERE id = ?", (member_id,)
        ).fetchone()
        # 없는 멤버에도 대조를 수행한다. 응답 시간 차이로 명단을 추측하지 못하게.
        _check_password(
            request,
            f"member:{member_id}",
            member_password,
            row["password_hash"] if row else None,
        )
        return Actor(member_id=member_id)

    return Actor()


def require_admin(actor: Actor) -> None:
    if not actor.is_admin:
        raise Forbidden("관리자만 할 수 있습니다.")


def require_self_or_admin(actor: Actor, member_id: int) -> None:
    if actor.is_admin:
        return
    if actor.member_id == member_id:
        return
    raise Forbidden("본인 또는 관리자만 수정할 수 있습니다.")
