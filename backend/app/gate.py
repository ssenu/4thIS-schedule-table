"""사이트 입장 비밀번호.

시간표 데이터는 주소만 알면 누구나 받아갈 수 있어서 API 앞에 한 겹을 둔다.
bcrypt 검증은 100ms 안팎이 걸리는데 화면이 15초마다 폴링하므로, 통과한
비밀번호의 지문만 기억해 두고 두 번째부터는 건너뛴다.
"""

import hashlib
import sqlite3

from app.auth import hash_password, verify_password
from app.db import get_setting, set_setting

GATE_HASH_KEY = "gate_password_hash"
GATE_TITLE_KEY = "gate_title"
GATE_INTRO_KEY = "gate_intro"

DEFAULT_TITLE = "동아리 주간 시간표"
DEFAULT_INTRO = "동아리원만 볼 수 있습니다. 받은 비밀번호를 넣어 주세요."

TITLE_MAX_LEN = 40
INTRO_MAX_LEN = 500
MIN_GATE_PASSWORD_LEN = 4


class GateKeeper:
    """통과한 비밀번호를 기억한다. 평문이 아니라 지문만 담는다."""

    def __init__(self) -> None:
        self._passed: set[str] = set()

    def check(self, conn: sqlite3.Connection, raw: str) -> bool:
        if not raw:
            return False
        fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if fingerprint in self._passed:
            return True
        stored = get_setting(conn, GATE_HASH_KEY)
        if stored is None or not verify_password(raw, stored):
            return False
        self._passed.add(fingerprint)
        return True

    def reset(self) -> None:
        """비밀번호가 바뀌면 기억을 버린다. 모두 다시 입력하게 된다."""
        self._passed.clear()


def read_gate(conn: sqlite3.Connection) -> dict[str, str]:
    title = get_setting(conn, GATE_TITLE_KEY)
    intro = get_setting(conn, GATE_INTRO_KEY)
    return {
        "title": DEFAULT_TITLE if title is None else title,
        "intro": DEFAULT_INTRO if intro is None else intro,
    }


def write_gate(
    conn: sqlite3.Connection,
    *,
    title: str | None = None,
    intro: str | None = None,
) -> None:
    if title is not None:
        set_setting(conn, GATE_TITLE_KEY, title)
    if intro is not None:
        set_setting(conn, GATE_INTRO_KEY, intro)


def set_gate_password(conn: sqlite3.Connection, raw: str) -> None:
    set_setting(conn, GATE_HASH_KEY, hash_password(raw))


def seed_gate(conn: sqlite3.Connection, password: str) -> None:
    """비어 있을 때만 세운다.

    ADMIN_PASSWORD 는 서버를 띄울 때마다 관리자 해시를 덮어쓰지만, 입장
    비밀번호는 관리자가 사이트에서 바꾼다. 매번 덮어쓰면 재시작할 때마다
    환경변수 값으로 되돌아가 버린다.
    """
    if get_setting(conn, GATE_HASH_KEY) is None:
        set_gate_password(conn, password)
    if get_setting(conn, GATE_TITLE_KEY) is None:
        set_setting(conn, GATE_TITLE_KEY, DEFAULT_TITLE)
    if get_setting(conn, GATE_INTRO_KEY) is None:
        set_setting(conn, GATE_INTRO_KEY, DEFAULT_INTRO)
