"""비밀번호 해시와 무차별 대입 방어.

4자리 숫자는 경우의 수가 10,000개뿐이라 시도 제한이 없으면 금방 뚫린다.
카운터는 프로세스 메모리에 있으므로 uvicorn 워커는 1개로 배포해야 한다.
"""

import time
from dataclasses import dataclass, field
from typing import Callable

import bcrypt

from app.constants import LOCKOUT_SECONDS, MAX_FAILED_ATTEMPTS


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
