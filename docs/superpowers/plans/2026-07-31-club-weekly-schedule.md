# 동아리 주간 시간표 웹 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동아리원이 계정 없이 4자리 비밀번호로 본인의 매주 반복 일정을 등록하고, 여러 명의 주간 시간표를 엑셀형 격자에 나란히 놓고 비교하는 웹 앱을 만든다.

**Architecture:** FastAPI 단일 프로세스가 JSON API와 빌드된 Vue 정적 파일을 함께 서빙하고, SQLite 파일 하나에 저장한다. 세션 없이 모든 쓰기 요청에 비밀번호를 헤더로 동봉해 서버가 매번 bcrypt 해시를 대조한다. 시간은 30분 단위 정수 슬롯으로 다뤄 겹침 검사와 CSS Grid 배치를 정수 연산으로 끝낸다.

**Tech Stack:** Python 3.11+ / FastAPI / Pydantic v2 / 표준 라이브러리 sqlite3 / bcrypt / pytest — Vue 3 / TypeScript / Vite / Pinia / vuedraggable / Vitest

**Spec:** `docs/superpowers/specs/2026-07-31-club-weekly-schedule-design.md`

## Global Constraints

이 절의 값은 모든 태스크의 요구사항에 암묵적으로 포함된다. 스펙에서 그대로 옮긴 값이므로 임의로 바꾸지 않는다.

- **시간 슬롯**: 06:00~24:00을 30분 단위로 자른 36칸. `slot = (hour - 6) * 2 + (minute >= 30 ? 1 : 0)`
- **`start_slot`**: 0 이상 35 이하 (포함). **`end_slot`**: 1 이상 36 이하 (**미포함/exclusive**). 항상 `start_slot < end_slot`
- **`day_of_week`**: 0 = 월요일 … 6 = 일요일. **날짜·월·주차·연도 개념은 코드 어디에도 넣지 않는다**
- **겹침 판정식**: `a.start_slot < b.end_slot and b.start_slot < a.end_slot` (끝=시작인 인접 일정은 겹치지 않음)
- **멤버 비밀번호**: 정확히 4자리 숫자, 정규식 `^\d{4}$`. **관리자 비밀번호**: 길이 제한 없는 자유 문자열
- **비밀번호 저장**: bcrypt 해시만. 평문은 DB·로그·API 응답 어디에도 남기지 않는다
- **시도 제한**: (클라이언트 IP, 대상) 조합으로 실패 10회 시 600초 잠금
- **uvicorn 워커는 1개**. 시도 제한 카운터가 프로세스 메모리에 있기 때문
- **일정 제목**: 1자 이상 30자 이하
- **색상**: 아래 10색 팔레트 중 하나의 hex 문자열만 허용

```
#ef4444  #f97316  #eab308  #22c55e  #14b8a6
#3b82f6  #6366f1  #a855f7  #ec4899  #78716c
```

- **권한 요약**: 카테고리 CRUD·카테고리 순서·멤버 소속 이동·멤버 순서는 **관리자 전용**. 일정 CRUD·이름 변경·비밀번호 변경·계정 삭제는 **본인 또는 관리자**. 멤버 등록은 **익명 허용**

## 파일 구조

```
backend/
  pyproject.toml            의존성, pytest 설정
  app/
    __init__.py
    constants.py            슬롯 상수, 팔레트, 제한값 — 다른 모듈이 여기서만 가져온다
    timeslot.py             슬롯 <-> "HH:MM" 변환, 겹침 판정
    config.py               환경변수 읽기
    db.py                   커넥션, 스키마 생성, 시드
    auth.py                 해시, 시도 제한기, Actor 판정, 권한 가드
    schemas.py              Pydantic 입출력 모델
    errors.py               도메인 예외 -> HTTP 응답 변환
    routers/
      __init__.py
      board.py              GET /api/board
      auth.py               POST /api/auth/verify
      categories.py         카테고리 CRUD + 순서
      members.py            멤버 CRUD + 순서
      schedules.py          일정 CRUD
    main.py                 앱 조립, 라우터 등록, 정적 파일 서빙
  tests/
    conftest.py             임시 DB + TestClient 픽스처
    test_timeslot.py  test_auth.py  test_actor.py  test_board.py
    test_categories.py  test_members.py  test_schedules.py
frontend/
  package.json  vite.config.ts  tsconfig.json  index.html
  src/
    main.ts  App.vue  types.ts  style.css  vuedraggable.d.ts
    constants.ts            팔레트·요일명 (백엔드 constants.py와 짝)
    utils/timeSlot.ts       슬롯 <-> 시간 변환
    utils/gridLayout.ts     격자 열 구성과 블록 배치 계산 (순수 함수)
    api/client.ts           fetch 래퍼, 인증 헤더 부착
    stores/board.ts         Pinia 스토어
    components/
      BaseDialog.vue    모달 껍데기 (4개 다이얼로그가 공유)
      MemberPanel.vue   카테고리별 이름 칩, 선택, 관리자 드래그
      CategoryEditor.vue  관리자용 카테고리 CRUD
      MemberDialog.vue  이름 등록/수정/삭제
      ScheduleGrid.vue  격자 렌더링
      MyScheduleList.vue  내 일정 텍스트 목록
      ScheduleDialog.vue  일정 추가/수정 폼
      UnlockDialog.vue  비밀번호 입력
      ErrorBanner.vue   상단 오류 배너
  tests/
    timeSlot.spec.ts  gridLayout.spec.ts  client.spec.ts  board.spec.ts
Dockerfile
.gitignore
README.md
```

**분리 원칙:** 계산은 순수 함수로 빼고 컴포넌트는 렌더링만 한다. `gridLayout.ts`가 "어느 열 어느 행"을 계산하고 `ScheduleGrid.vue`는 그 결과를 그리기만 하므로, 격자 배치 규칙을 컴포넌트를 띄우지 않고 테스트할 수 있다. 백엔드도 같은 이유로 `timeslot.py`와 `auth.py`를 라우터에서 분리한다.

---

### Task 1: 프로젝트 뼈대와 시간 슬롯 유틸

**Files:**
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/constants.py`
- Create: `backend/app/timeslot.py`
- Test: `backend/tests/test_timeslot.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `app.constants`: `DAY_START_HOUR: int`, `SLOT_MINUTES: int`, `SLOT_COUNT: int`, `DAY_NAMES: list[str]`, `PALETTE: list[str]`, `TITLE_MAX_LEN: int`, `NAME_MAX_LEN: int`, `MEMBER_PASSWORD_PATTERN: str`, `MAX_FAILED_ATTEMPTS: int`, `LOCKOUT_SECONDS: int`, `DEFAULT_CATEGORIES: list[str]`
  - `app.timeslot.slot_to_time(slot: int) -> str`
  - `app.timeslot.time_to_slot(text: str) -> int`
  - `app.timeslot.describe(day_of_week: int, start_slot: int, end_slot: int) -> str`
  - `app.timeslot.overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool`

- [ ] **Step 1: git 저장소와 무시 파일 만들기**

프로젝트 루트에서 실행한다.

```bash
git init
```

`.gitignore`:

```
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
data/
*.db
node_modules/
dist/
.DS_Store
```

- [ ] **Step 2: 파이썬 프로젝트 설정 파일 작성**

`backend/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "club-schedule-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "bcrypt>=4.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.27"]

# backend/ 아래에 app/ 과 tests/ 가 나란히 있어서 자동 탐색이 실패한다. 명시한다.
[tool.setuptools]
packages = ["app", "app.routers"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: 가상환경 만들고 의존성 설치**

`backend/` 디렉터리에서 실행한다.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

기대 출력: 마지막 줄에 `Successfully installed ... club-schedule-backend-0.1.0 ...`

이후 모든 파이썬 명령은 `backend/`에서 `.venv/Scripts/python -m ...` 형태로 실행한다.

- [ ] **Step 4: 실패하는 테스트 작성**

`backend/tests/test_timeslot.py`:

```python
import pytest

from app.constants import SLOT_COUNT
from app.timeslot import describe, overlaps, slot_to_time, time_to_slot


def test_slot_zero_is_day_start():
    assert slot_to_time(0) == "06:00"


def test_slot_six_is_nine_am():
    assert slot_to_time(6) == "09:00"


def test_last_slot_boundary_is_midnight():
    assert slot_to_time(SLOT_COUNT) == "24:00"


def test_half_hour_slots():
    assert slot_to_time(1) == "06:30"
    assert slot_to_time(35) == "23:30"


@pytest.mark.parametrize("slot", range(SLOT_COUNT + 1))
def test_round_trip(slot):
    assert time_to_slot(slot_to_time(slot)) == slot


def test_time_to_slot_rejects_off_grid_minutes():
    with pytest.raises(ValueError):
        time_to_slot("09:15")


def test_time_to_slot_rejects_before_day_start():
    with pytest.raises(ValueError):
        time_to_slot("05:30")


def test_describe_reads_as_a_sentence():
    assert describe(0, 6, 14) == "월 09:00~13:00"
    assert describe(6, 0, 1) == "일 06:00~06:30"


def test_overlapping_ranges():
    assert overlaps(6, 10, 8, 12) is True
    assert overlaps(6, 10, 0, 36) is True


def test_adjacent_ranges_do_not_overlap():
    assert overlaps(6, 10, 10, 14) is False
    assert overlaps(10, 14, 6, 10) is False


def test_disjoint_ranges_do_not_overlap():
    assert overlaps(6, 10, 20, 24) is False
```

- [ ] **Step 5: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_timeslot.py -v
```

기대 출력: `ModuleNotFoundError: No module named 'app.constants'` 로 수집 단계에서 실패

- [ ] **Step 6: 상수 모듈 작성**

`backend/app/__init__.py`: 빈 파일로 만든다.

`backend/app/constants.py`:

```python
"""스펙에 고정된 값. 다른 모듈은 숫자를 직접 쓰지 않고 여기서 가져온다."""

DAY_START_HOUR = 6
SLOT_MINUTES = 30
SLOT_COUNT = 36  # 06:00 ~ 24:00

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

PALETTE = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#14b8a6",
    "#3b82f6",
    "#6366f1",
    "#a855f7",
    "#ec4899",
    "#78716c",
]

NAME_MAX_LEN = 20
TITLE_MAX_LEN = 30
MEMBER_PASSWORD_PATTERN = r"^\d{4}$"

MAX_FAILED_ATTEMPTS = 10
LOCKOUT_SECONDS = 600

DEFAULT_CATEGORIES = ["1학년", "2학년", "3학년"]
```

- [ ] **Step 7: 시간 슬롯 모듈 작성**

`backend/app/timeslot.py`:

```python
"""30분 단위 슬롯 정수와 사람이 읽는 시간 문자열 사이의 변환."""

from app.constants import DAY_NAMES, DAY_START_HOUR, SLOT_COUNT, SLOT_MINUTES


def slot_to_time(slot: int) -> str:
    """슬롯 번호를 "HH:MM"으로 바꾼다. slot=SLOT_COUNT는 "24:00"이다."""
    if not 0 <= slot <= SLOT_COUNT:
        raise ValueError(f"슬롯 범위를 벗어났습니다: {slot}")
    minutes = DAY_START_HOUR * 60 + slot * SLOT_MINUTES
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_to_slot(text: str) -> int:
    """"HH:MM"을 슬롯 번호로 바꾼다. 격자에 없는 시각은 거부한다."""
    hour_text, _, minute_text = text.partition(":")
    minutes = int(hour_text) * 60 + int(minute_text)
    offset = minutes - DAY_START_HOUR * 60
    if offset < 0 or offset % SLOT_MINUTES != 0:
        raise ValueError(f"격자에 없는 시각입니다: {text}")
    slot = offset // SLOT_MINUTES
    if slot > SLOT_COUNT:
        raise ValueError(f"격자에 없는 시각입니다: {text}")
    return slot


def describe(day_of_week: int, start_slot: int, end_slot: int) -> str:
    """"월 09:00~13:00" 형태의 한 줄 설명. 오류 메시지와 툴팁에 쓴다."""
    return (
        f"{DAY_NAMES[day_of_week]} "
        f"{slot_to_time(start_slot)}~{slot_to_time(end_slot)}"
    )


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """두 구간이 겹치는지 판정한다. 끝과 시작이 맞닿는 경우는 겹치지 않는다."""
    return a_start < b_end and b_start < a_end
```

- [ ] **Step 8: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_timeslot.py -v
```

기대 출력: `47 passed` (파라미터화된 왕복 테스트 37개 포함)

- [ ] **Step 9: 커밋**

```bash
git add .gitignore backend/pyproject.toml backend/app backend/tests
git commit -m "feat: add time slot conversion and shared constants"
```

---

### Task 2: 데이터베이스 스키마와 초기 시드

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: `app.constants.DEFAULT_CATEGORIES`
- Produces:
  - `app.config.Settings` — 속성 `db_path: Path`, `admin_password: str`
  - `app.config.load_settings() -> Settings`
  - `app.db.connect(db_path: Path) -> sqlite3.Connection` (row_factory는 `sqlite3.Row`, 외래키 ON)
  - `app.db.initialize(conn: sqlite3.Connection, admin_password_hash: str) -> None`
  - `app.db.get_setting(conn, key: str) -> str | None`
  - `app.db.set_setting(conn, key: str, value: str) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_db.py`:

```python
import sqlite3

import pytest

from app.constants import DEFAULT_CATEGORIES
from app.db import connect, get_setting, initialize


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, "hashed-admin")
    yield connection
    connection.close()


def test_tables_exist(conn):
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"categories", "members", "schedules", "settings"} <= names


def test_default_categories_are_seeded(conn):
    rows = conn.execute("SELECT name FROM categories ORDER BY sort_order").fetchall()
    assert [row["name"] for row in rows] == DEFAULT_CATEGORIES


def test_admin_hash_is_stored(conn):
    assert get_setting(conn, "admin_password_hash") == "hashed-admin"


def test_initialize_is_idempotent(conn):
    initialize(conn, "hashed-admin")
    count = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    assert count == len(DEFAULT_CATEGORIES)


def test_initialize_updates_admin_hash(conn):
    initialize(conn, "new-hash")
    assert get_setting(conn, "admin_password_hash") == "new-hash"


def test_rows_are_dict_like(conn):
    row = conn.execute("SELECT id, name FROM categories LIMIT 1").fetchone()
    assert row["name"] == DEFAULT_CATEGORIES[0]


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES ('없는사람', 999, 'x', 0)"
        )


def test_deleting_member_cascades_to_schedules(conn):
    category_id = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()["id"]
    cursor = conn.execute(
        "INSERT INTO members (name, category_id, password_hash, sort_order)"
        " VALUES ('철수', ?, 'x', 0)",
        (category_id,),
    )
    member_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 9, '전공수업', '#ef4444')",
        (member_id,),
    )
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    remaining = conn.execute("SELECT COUNT(*) AS n FROM schedules").fetchone()["n"]
    assert remaining == 0


def test_schedule_rejects_reversed_range(conn):
    category_id = conn.execute("SELECT id FROM categories LIMIT 1").fetchone()["id"]
    cursor = conn.execute(
        "INSERT INTO members (name, category_id, password_hash, sort_order)"
        " VALUES ('영희', ?, 'x', 0)",
        (category_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO schedules"
            " (member_id, day_of_week, start_slot, end_slot, title, color)"
            " VALUES (?, 0, 10, 6, '거꾸로', '#ef4444')",
            (cursor.lastrowid,),
        )
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_db.py -v
```

기대 출력: `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: 설정 모듈 작성**

`backend/app/config.py`:

```python
"""환경변수에서 읽는 배포 설정."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    admin_password: str


def load_settings() -> Settings:
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        raise RuntimeError("환경변수 ADMIN_PASSWORD를 설정해 주세요.")
    db_path = Path(os.environ.get("DB_PATH", "./data/schedule.db"))
    return Settings(db_path=db_path, admin_password=admin_password)
```

- [ ] **Step 4: DB 모듈 작성**

`backend/app/db.py`:

```python
"""SQLite 커넥션과 스키마. 날짜 컬럼은 어디에도 없다 — 시간표는 반복되는 한 주다."""

import sqlite3
from pathlib import Path

from app.constants import DEFAULT_CATEGORIES

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    category_id   INTEGER NOT NULL REFERENCES categories(id),
    password_hash TEXT    NOT NULL,
    sort_order    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id   INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_slot  INTEGER NOT NULL CHECK (start_slot BETWEEN 0 AND 35),
    end_slot    INTEGER NOT NULL CHECK (end_slot   BETWEEN 1 AND 36),
    title       TEXT    NOT NULL,
    color       TEXT    NOT NULL,
    CHECK (start_slot < end_slot)
);

CREATE INDEX IF NOT EXISTS idx_schedules_member_day
    ON schedules(member_id, day_of_week);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """커넥션을 연다. 행은 이름으로 접근하고, 외래키 제약을 켠다."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(conn: sqlite3.Connection, admin_password_hash: str) -> None:
    """스키마를 만들고 기본 카테고리를 시드한다. 여러 번 불러도 안전하다."""
    conn.executescript(SCHEMA)
    existing = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    if existing == 0:
        conn.executemany(
            "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
            [(name, index) for index, name in enumerate(DEFAULT_CATEGORIES)],
        )
    set_setting(conn, "admin_password_hash", admin_password_hash)


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
```

`executescript`는 열려 있는 트랜잭션을 커밋하므로 `connect`에서 `isolation_level=None`(자동 커밋)을 쓴다. 이 앱은 요청당 쓰기가 한두 건이라 명시적 트랜잭션이 필요 없다.

- [ ] **Step 5: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_db.py -v
```

기대 출력: `9 passed`

- [ ] **Step 6: 커밋**

```bash
git add backend/app/config.py backend/app/db.py backend/tests/test_db.py
git commit -m "feat: add sqlite schema, seeding, and settings loader"
```

---

### Task 3: 비밀번호 해시와 시도 제한

**Files:**
- Create: `backend/app/auth.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.constants.MAX_FAILED_ATTEMPTS`, `app.constants.LOCKOUT_SECONDS`
- Produces:
  - `app.auth.hash_password(raw: str) -> str`
  - `app.auth.verify_password(raw: str, hashed: str) -> bool`
  - `app.auth.AttemptLimiter(max_attempts: int, lockout_seconds: int, clock: Callable[[], float])` — 메서드 `check(key: str) -> None` (잠겨 있으면 `LockedOut` 발생), `record_failure(key: str) -> int` (남은 시도 횟수 반환), `record_success(key: str) -> None`
  - `app.auth.LockedOut(Exception)` — 속성 `retry_after: int`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_auth.py`:

```python
import pytest

from app.auth import AttemptLimiter, LockedOut, hash_password, verify_password


def test_hash_is_not_plaintext():
    hashed = hash_password("1234")
    assert hashed != "1234"
    assert len(hashed) > 20


def test_verify_accepts_correct_password():
    assert verify_password("1234", hash_password("1234")) is True


def test_verify_rejects_wrong_password():
    assert verify_password("9999", hash_password("1234")) is False


def test_same_password_hashes_differently_each_time():
    assert hash_password("1234") != hash_password("1234")


def test_verify_survives_a_malformed_hash():
    assert verify_password("1234", "not-a-bcrypt-hash") is False


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return AttemptLimiter(max_attempts=3, lockout_seconds=600, clock=clock)


def test_fresh_key_is_allowed(limiter):
    limiter.check("1.2.3.4:member:1")


def test_remaining_attempts_count_down(limiter):
    assert limiter.record_failure("k") == 2
    assert limiter.record_failure("k") == 1
    assert limiter.record_failure("k") == 0


def test_lockout_after_max_attempts(limiter):
    for _ in range(3):
        limiter.record_failure("k")
    with pytest.raises(LockedOut):
        limiter.check("k")


def test_lockout_reports_retry_after(limiter):
    for _ in range(3):
        limiter.record_failure("k")
    with pytest.raises(LockedOut) as excinfo:
        limiter.check("k")
    assert excinfo.value.retry_after == 601


def test_lockout_expires(limiter, clock):
    for _ in range(3):
        limiter.record_failure("k")
    clock.advance(601)
    limiter.check("k")


def test_success_clears_failures(limiter):
    limiter.record_failure("k")
    limiter.record_failure("k")
    limiter.record_success("k")
    assert limiter.record_failure("k") == 2


def test_keys_are_tracked_independently(limiter):
    for _ in range(3):
        limiter.record_failure("a")
    limiter.check("b")
```

`retry_after`가 601인 것은 남은 시간을 올림 처리하기 때문이다. 600.0초가 남았을 때 600을 돌려주면 그 시각에 다시 시도해도 아직 잠겨 있다.

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_auth.py -v
```

기대 출력: `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: 인증 모듈 작성**

`backend/app/auth.py`:

```python
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
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_auth.py -v
```

기대 출력: `13 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/app/auth.py backend/tests/test_auth.py
git commit -m "feat: add password hashing and attempt limiter"
```

---

### Task 4: 앱 조립과 GET /api/board

**Files:**
- Create: `backend/app/errors.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/board.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_board.py`

**Interfaces:**
- Consumes: `app.db.connect`, `app.db.initialize`, `app.config.load_settings`, `app.auth.hash_password`, `app.auth.AttemptLimiter`
- Produces:
  - `app.errors.DomainError(Exception)` — 속성 `status_code: int`, `detail: str`
  - `app.errors.Unauthorized`(401), `Forbidden`(403), `NotFound`(404), `Conflict`(409), `TooManyAttempts`(429, 속성 `retry_after`)
  - `app.schemas.CategoryOut`, `MemberOut`, `ScheduleOut`, `BoardOut`
  - `app.main.create_app(conn: sqlite3.Connection, limiter: AttemptLimiter) -> FastAPI`
  - `app.main.app` — 운영용 인스턴스
  - FastAPI 상태: `app.state.conn`, `app.state.limiter`
  - 의존성 `app.routers.board.get_conn(request) -> sqlite3.Connection`
  - 테스트 픽스처: `clock`, `conn`, `limiter`, `client`, `admin_headers`, `category_id`, `make_member`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.auth import AttemptLimiter, hash_password
from app.db import connect, initialize
from app.main import create_app

ADMIN_PASSWORD = "admin-secret"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, hash_password(ADMIN_PASSWORD))
    yield connection
    connection.close()


@pytest.fixture
def limiter(clock):
    return AttemptLimiter(max_attempts=10, lockout_seconds=600, clock=clock)


@pytest.fixture
def client(conn, limiter):
    with TestClient(create_app(conn, limiter)) as test_client:
        yield test_client


@pytest.fixture
def admin_headers():
    return {"X-Admin-Password": ADMIN_PASSWORD}


@pytest.fixture
def category_id(conn):
    return conn.execute(
        "SELECT id FROM categories ORDER BY sort_order"
    ).fetchone()["id"]


@pytest.fixture
def make_member(conn, category_id):
    """(id, headers)를 돌려주는 헬퍼. headers는 그 멤버 자격의 인증 헤더다."""

    def _make(
        name: str, password: str = "1234", cat_id: int | None = None
    ) -> tuple[int, dict]:
        target = cat_id or category_id
        cursor = conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES (?, ?, ?,"
            "   (SELECT COALESCE(MAX(sort_order) + 1, 0) FROM members"
            "    WHERE category_id = ?))",
            (name, target, hash_password(password), target),
        )
        member_id = cursor.lastrowid
        headers = {"X-Member-Id": str(member_id), "X-Member-Password": password}
        return member_id, headers

    return _make
```

`backend/tests/test_board.py`:

```python
from app.auth import hash_password
from app.constants import DEFAULT_CATEGORIES


def test_board_returns_seeded_categories(client):
    body = client.get("/api/board").json()
    assert [c["name"] for c in body["categories"]] == DEFAULT_CATEGORIES


def test_board_has_all_three_collections(client):
    body = client.get("/api/board").json()
    assert set(body) == {"categories", "members", "schedules"}


def test_board_is_empty_of_members_at_first(client):
    body = client.get("/api/board").json()
    assert body["members"] == []
    assert body["schedules"] == []


def test_board_lists_members_and_schedules(client, conn, make_member):
    member_id, _ = make_member("철수")
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 14, '전공수업', '#ef4444')",
        (member_id,),
    )
    body = client.get("/api/board").json()
    assert body["members"][0]["name"] == "철수"
    schedule = body["schedules"][0]
    assert (schedule["start_slot"], schedule["end_slot"]) == (6, 14)
    assert schedule["title"] == "전공수업"


def test_board_never_leaks_password_hash(client, make_member):
    make_member("철수")
    response = client.get("/api/board")
    assert "password_hash" not in response.json()["members"][0]
    assert "1234" not in response.text


def test_board_orders_by_sort_order(client, conn, category_id):
    for index, name in enumerate(["다", "가", "나"]):
        conn.execute(
            "INSERT INTO members (name, category_id, password_hash, sort_order)"
            " VALUES (?, ?, ?, ?)",
            (name, category_id, hash_password("1234"), 2 - index),
        )
    body = client.get("/api/board").json()
    assert [m["name"] for m in body["members"]] == ["나", "가", "다"]
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_board.py -v
```

기대 출력: `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: 도메인 예외 모듈 작성**

`backend/app/errors.py`:

```python
"""라우터가 던지고 main.py의 핸들러가 HTTP 응답으로 바꾸는 예외."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Unauthorized(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class TooManyAttempts(DomainError):
    status_code = 429

    def __init__(self, detail: str, retry_after: int):
        super().__init__(detail)
        self.retry_after = retry_after
```

- [ ] **Step 4: 출력 스키마 작성**

`backend/app/schemas.py`:

```python
"""API 입출력 모델. 출력 모델에는 password_hash가 절대 들어가지 않는다."""

from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int


class MemberOut(BaseModel):
    id: int
    name: str
    category_id: int
    sort_order: int


class ScheduleOut(BaseModel):
    id: int
    member_id: int
    day_of_week: int
    start_slot: int
    end_slot: int
    title: str
    color: str


class BoardOut(BaseModel):
    categories: list[CategoryOut]
    members: list[MemberOut]
    schedules: list[ScheduleOut]
```

- [ ] **Step 5: board 라우터 작성**

`backend/app/routers/__init__.py`: 빈 파일로 만든다.

`backend/app/routers/board.py`:

```python
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
```

- [ ] **Step 6: 앱 조립 모듈 작성**

`backend/app/main.py`:

```python
"""FastAPI 앱 조립. 커넥션과 시도 제한기를 밖에서 주입받아 테스트가 쉽다."""

import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth import AttemptLimiter, hash_password
from app.config import load_settings
from app.db import connect, initialize
from app.errors import DomainError, TooManyAttempts
from app.routers import board


def create_app(conn: sqlite3.Connection, limiter: AttemptLimiter) -> FastAPI:
    app = FastAPI(title="동아리 주간 시간표")
    app.state.conn = conn
    app.state.limiter = limiter

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        headers = {}
        if isinstance(exc, TooManyAttempts):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )

    app.include_router(board.router)
    return app


def _build_production_app() -> FastAPI:
    settings = load_settings()
    conn = connect(settings.db_path)
    initialize(conn, hash_password(settings.admin_password))
    return create_app(conn, AttemptLimiter())


app = _build_production_app()
```

`app = _build_production_app()`는 `ADMIN_PASSWORD`가 없으면 임포트 시점에 예외를 던진다. 테스트는 `create_app`만 쓰므로 영향받지 않는다.

- [ ] **Step 7: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_board.py -v
```

기대 출력: `6 passed`

- [ ] **Step 8: 커밋**

```bash
git add backend/app backend/tests
git commit -m "feat: add app factory, domain errors, and board endpoint"
```

---

### Task 5: Actor 판정과 권한 가드

**Files:**
- Modify: `backend/app/auth.py` (임포트 추가 + 모듈 끝에 추가)
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py` (라우터 등록)
- Test: `backend/tests/test_actor.py`

**Interfaces:**
- Consumes: `app.auth.verify_password`, `app.auth.AttemptLimiter`, `app.db.get_setting`, `app.errors.Forbidden`, `app.errors.TooManyAttempts`, `app.errors.Unauthorized`
- Produces:
  - `app.auth.Actor` — 동결 데이터클래스, 속성 `is_admin: bool`, `member_id: int | None`, 프로퍼티 `is_anonymous: bool`
  - `app.auth.resolve_actor(request: Request) -> Actor` — FastAPI 의존성으로 쓴다
  - `app.auth.require_admin(actor: Actor) -> None`
  - `app.auth.require_self_or_admin(actor: Actor, member_id: int) -> None`
  - `POST /api/auth/verify`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_actor.py`:

```python
def test_verify_accepts_admin(client, admin_headers):
    response = client.post(
        "/api/auth/verify", json={"scope": "admin"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_verify_rejects_wrong_admin_password(client):
    response = client.post(
        "/api/auth/verify",
        json={"scope": "admin"},
        headers={"X-Admin-Password": "틀린값"},
    )
    assert response.status_code == 401


def test_verify_accepts_member(client, make_member):
    member_id, headers = make_member("철수")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers=headers,
    )
    assert response.status_code == 200


def test_verify_rejects_wrong_member_password(client, make_member):
    member_id, _ = make_member("철수", password="1234")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers={"X-Member-Id": str(member_id), "X-Member-Password": "9999"},
    )
    assert response.status_code == 401


def test_failure_message_reports_remaining_attempts(client, make_member):
    member_id, _ = make_member("철수")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": member_id},
        headers={"X-Member-Id": str(member_id), "X-Member-Password": "9999"},
    )
    assert "9" in response.json()["detail"]


def test_lockout_after_ten_failures(client, make_member):
    member_id, _ = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    response = client.post("/api/auth/verify", json=body, headers=bad)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "601"


def test_lockout_blocks_even_the_correct_password(client, make_member):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    assert client.post("/api/auth/verify", json=body, headers=good).status_code == 429


def test_lockout_expires(client, make_member, clock):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(10):
        client.post("/api/auth/verify", json=body, headers=bad)
    clock.advance(601)
    assert client.post("/api/auth/verify", json=body, headers=good).status_code == 200


def test_success_resets_the_counter(client, make_member):
    member_id, good = make_member("철수")
    bad = {"X-Member-Id": str(member_id), "X-Member-Password": "9999"}
    body = {"scope": "member", "member_id": member_id}
    for _ in range(9):
        client.post("/api/auth/verify", json=body, headers=bad)
    client.post("/api/auth/verify", json=body, headers=good)
    response = client.post("/api/auth/verify", json=body, headers=bad)
    assert "9" in response.json()["detail"]


def test_verify_rejects_unknown_member(client):
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": 999},
        headers={"X-Member-Id": "999", "X-Member-Password": "1234"},
    )
    assert response.status_code == 401


def test_verify_member_scope_requires_matching_header(client, make_member):
    _, first_headers = make_member("철수")
    second_id, _ = make_member("영희")
    response = client.post(
        "/api/auth/verify",
        json={"scope": "member", "member_id": second_id},
        headers=first_headers,
    )
    assert response.status_code == 403


def test_admin_header_wins_over_member_header(client, make_member, admin_headers):
    _, member_headers = make_member("철수")
    merged = {**member_headers, **admin_headers}
    response = client.post("/api/auth/verify", json={"scope": "admin"}, headers=merged)
    assert response.status_code == 200
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_actor.py -v
```

기대 출력: 모든 테스트가 404로 실패

- [ ] **Step 3: auth.py 임포트를 보강**

`backend/app/auth.py` 상단 임포트 블록을 아래로 교체한다.

```python
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable

import bcrypt
from fastapi import Request

from app.constants import LOCKOUT_SECONDS, MAX_FAILED_ATTEMPTS
from app.db import get_setting
from app.errors import Forbidden, TooManyAttempts, Unauthorized
```

- [ ] **Step 4: Actor 판정과 권한 가드를 auth.py 끝에 추가**

```python
@dataclass(frozen=True)
class Actor:
    """요청을 보낸 주체. 익명이면 둘 다 비어 있다."""

    is_admin: bool = False
    member_id: int | None = None

    @property
    def is_anonymous(self) -> bool:
        return not self.is_admin and self.member_id is None


def _client_key(request: Request, target: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{target}"


def _check_password(
    request: Request, target: str, raw: str, hashed: str | None
) -> bool:
    """시도 제한을 적용하며 비밀번호를 대조한다. 실패하면 예외를 던진다."""
    limiter: AttemptLimiter = request.app.state.limiter
    key = _client_key(request, target)
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

    admin_password = request.headers.get("X-Admin-Password")
    if admin_password:
        _check_password(
            request,
            "admin",
            admin_password,
            get_setting(conn, "admin_password_hash"),
        )
        return Actor(is_admin=True)

    member_id_header = request.headers.get("X-Member-Id")
    member_password = request.headers.get("X-Member-Password")
    if member_id_header and member_password:
        try:
            member_id = int(member_id_header)
        except ValueError as exc:
            raise Unauthorized("멤버 정보가 올바르지 않습니다.") from exc
        row = conn.execute(
            "SELECT password_hash FROM members WHERE id = ?", (member_id,)
        ).fetchone()
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
```

존재하지 않는 멤버에도 `_check_password`를 부르는 이유는, 있는 이름과 없는 이름의 응답 시간 차이로 회원 명단을 추측하지 못하게 하려는 것이다.

- [ ] **Step 5: auth 라우터 작성**

`backend/app/routers/auth.py`:

```python
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
```

- [ ] **Step 6: main.py에 라우터 등록**

`backend/app/main.py`의 `from app.routers import board` 를 아래로 바꾼다.

```python
from app.routers import auth as auth_router
from app.routers import board
```

`app.include_router(board.router)` 아래에 추가한다.

```python
    app.include_router(auth_router.router)
```

- [ ] **Step 7: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_actor.py -v
```

기대 출력: `12 passed`

- [ ] **Step 8: 전체 테스트를 돌려 회귀가 없는지 확인**

```bash
.venv/Scripts/python -m pytest -v
```

기대 출력: `87 passed`

- [ ] **Step 9: 커밋**

```bash
git add backend/app backend/tests
git commit -m "feat: add actor resolution, permission guards, and verify endpoint"
```

---

### Task 6: 카테고리 API (관리자 전용)

**Files:**
- Create: `backend/app/routers/categories.py`
- Modify: `backend/app/schemas.py` (입력 모델 추가)
- Modify: `backend/app/main.py` (라우터 등록)
- Test: `backend/tests/test_categories.py`

**Interfaces:**
- Consumes: `app.auth.resolve_actor`, `app.auth.require_admin`, `app.errors.Conflict`, `app.errors.NotFound`, `app.errors.DomainError`, `app.routers.board.get_conn`
- Produces:
  - `app.schemas.CategoryCreate` — `name: str`
  - `app.schemas.CategoryUpdate` — `name: str`
  - `app.schemas.OrderIn` — `ordered_ids: list[int]`
  - `POST /api/categories`, `PATCH /api/categories/{id}`, `DELETE /api/categories/{id}`, `PUT /api/categories/order`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_categories.py`:

```python
def test_create_requires_admin(client):
    assert client.post("/api/categories", json={"name": "4학년"}).status_code == 403


def test_member_cannot_create(client, make_member):
    _, headers = make_member("철수")
    response = client.post("/api/categories", json={"name": "4학년"}, headers=headers)
    assert response.status_code == 403


def test_admin_creates_category(client, admin_headers):
    response = client.post(
        "/api/categories", json={"name": "4학년"}, headers=admin_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "4학년"


def test_created_category_goes_last(client, admin_headers):
    client.post("/api/categories", json={"name": "4학년"}, headers=admin_headers)
    names = [c["name"] for c in client.get("/api/board").json()["categories"]]
    assert names[-1] == "4학년"


def test_duplicate_name_conflicts(client, admin_headers):
    client.post("/api/categories", json={"name": "4학년"}, headers=admin_headers)
    response = client.post(
        "/api/categories", json={"name": "4학년"}, headers=admin_headers
    )
    assert response.status_code == 409


def test_rename_category(client, admin_headers, category_id):
    response = client.patch(
        f"/api/categories/{category_id}",
        json={"name": "신입생"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "신입생"


def test_rename_unknown_category(client, admin_headers):
    response = client.patch(
        "/api/categories/999", json={"name": "x"}, headers=admin_headers
    )
    assert response.status_code == 404


def test_delete_empty_category(client, admin_headers, conn):
    target = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.delete(f"/api/categories/{target}", headers=admin_headers)
    assert response.status_code == 204


def test_delete_rejects_category_with_members(
    client, admin_headers, category_id, make_member
):
    make_member("철수")
    response = client.delete(f"/api/categories/{category_id}", headers=admin_headers)
    assert response.status_code == 409
    assert "1" in response.json()["detail"]


def test_cannot_delete_the_last_category(client, admin_headers, conn):
    ids = [row["id"] for row in conn.execute("SELECT id FROM categories")]
    for category in ids[:-1]:
        client.delete(f"/api/categories/{category}", headers=admin_headers)
    response = client.delete(f"/api/categories/{ids[-1]}", headers=admin_headers)
    assert response.status_code == 409


def test_reorder_categories(client, admin_headers, conn):
    rows = conn.execute("SELECT id FROM categories ORDER BY sort_order")
    ids = [row["id"] for row in rows]
    reversed_ids = list(reversed(ids))
    response = client.put(
        "/api/categories/order",
        json={"ordered_ids": reversed_ids},
        headers=admin_headers,
    )
    assert response.status_code == 200
    after = [c["id"] for c in client.get("/api/board").json()["categories"]]
    assert after == reversed_ids


def test_reorder_rejects_incomplete_list(client, admin_headers, conn):
    rows = conn.execute("SELECT id FROM categories ORDER BY sort_order")
    ids = [row["id"] for row in rows]
    response = client.put(
        "/api/categories/order", json={"ordered_ids": ids[:1]}, headers=admin_headers
    )
    assert response.status_code == 400


def test_reorder_requires_admin(client, conn):
    ids = [row["id"] for row in conn.execute("SELECT id FROM categories")]
    response = client.put("/api/categories/order", json={"ordered_ids": ids})
    assert response.status_code == 403


def test_blank_name_is_rejected(client, admin_headers):
    response = client.post("/api/categories", json={"name": ""}, headers=admin_headers)
    assert response.status_code == 422
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_categories.py -v
```

기대 출력: 대부분 405 Method Not Allowed 또는 404로 실패

- [ ] **Step 3: 입력 스키마 추가**

`backend/app/schemas.py` 상단 임포트를 아래로 바꾼다.

```python
from pydantic import BaseModel, Field

from app.constants import NAME_MAX_LEN
```

파일 끝에 추가한다.

```python
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)


class OrderIn(BaseModel):
    ordered_ids: list[int]
```

- [ ] **Step 4: 카테고리 라우터 작성**

`backend/app/routers/categories.py`:

```python
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
```

- [ ] **Step 5: main.py에 라우터 등록**

임포트에 다음 줄을 추가한다.

```python
from app.routers import categories
```

`app.include_router(auth_router.router)` 아래에 추가한다.

```python
    app.include_router(categories.router)
```

- [ ] **Step 6: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_categories.py -v
```

기대 출력: `14 passed`

- [ ] **Step 7: 커밋**

```bash
git add backend/app backend/tests/test_categories.py
git commit -m "feat: add admin-only category CRUD and reordering"
```

---

### Task 7: 멤버 API (필드별 권한)

**Files:**
- Create: `backend/app/routers/members.py`
- Modify: `backend/app/schemas.py` (입력 모델 추가)
- Modify: `backend/app/main.py` (라우터 등록)
- Test: `backend/tests/test_members.py`

**Interfaces:**
- Consumes: `app.auth.require_admin`, `app.auth.require_self_or_admin`, `app.auth.hash_password`, `app.errors.Forbidden`
- Produces:
  - `app.schemas.MemberCreate` — `name: str`, `category_id: int`, `password: str`
  - `app.schemas.MemberUpdate` — `name: str | None`, `password: str | None`, `category_id: int | None`
  - `app.schemas.MemberOrderIn` — `category_id: int`, `ordered_ids: list[int]`
  - `POST /api/members`, `PATCH /api/members/{id}`, `DELETE /api/members/{id}`, `PUT /api/members/order`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_members.py`:

```python
def test_anyone_can_register(client, category_id):
    response = client.post(
        "/api/members",
        json={"name": "철수", "category_id": category_id, "password": "1234"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "철수"


def test_registration_never_returns_the_password(client, category_id):
    response = client.post(
        "/api/members",
        json={"name": "철수", "category_id": category_id, "password": "1234"},
    )
    assert "password" not in response.text


def test_password_must_be_four_digits(client, category_id):
    for bad in ["123", "12345", "abcd", ""]:
        response = client.post(
            "/api/members",
            json={"name": f"이름{bad}", "category_id": category_id, "password": bad},
        )
        assert response.status_code == 422, bad


def test_duplicate_name_conflicts(client, category_id):
    body = {"name": "철수", "category_id": category_id, "password": "1234"}
    client.post("/api/members", json=body)
    assert client.post("/api/members", json=body).status_code == 409


def test_unknown_category_is_rejected(client):
    response = client.post(
        "/api/members", json={"name": "철수", "category_id": 999, "password": "1234"}
    )
    assert response.status_code == 404


def test_self_can_rename(client, make_member):
    member_id, headers = make_member("철수")
    response = client.patch(
        f"/api/members/{member_id}", json={"name": "철수2"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "철수2"


def test_admin_can_rename_anyone(client, make_member, admin_headers):
    member_id, _ = make_member("철수")
    response = client.patch(
        f"/api/members/{member_id}", json={"name": "철수2"}, headers=admin_headers
    )
    assert response.status_code == 200


def test_other_member_cannot_rename(client, make_member):
    target_id, _ = make_member("철수")
    _, other_headers = make_member("영희")
    response = client.patch(
        f"/api/members/{target_id}", json={"name": "해킹"}, headers=other_headers
    )
    assert response.status_code == 403


def test_anonymous_cannot_rename(client, make_member):
    member_id, _ = make_member("철수")
    response = client.patch(f"/api/members/{member_id}", json={"name": "x"})
    assert response.status_code == 403


def test_self_can_change_password(client, make_member):
    member_id, headers = make_member("철수", password="1234")
    changed = client.patch(
        f"/api/members/{member_id}", json={"password": "5678"}, headers=headers
    )
    assert changed.status_code == 200
    new_headers = {"X-Member-Id": str(member_id), "X-Member-Password": "5678"}
    again = client.patch(
        f"/api/members/{member_id}", json={"name": "철수3"}, headers=new_headers
    )
    assert again.status_code == 200


def test_self_cannot_move_category(client, make_member, conn):
    member_id, headers = make_member("철수")
    other = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.patch(
        f"/api/members/{member_id}", json={"category_id": other}, headers=headers
    )
    assert response.status_code == 403
    assert "관리자" in response.json()["detail"]


def test_admin_can_move_category(client, make_member, admin_headers, conn):
    member_id, _ = make_member("철수")
    other = conn.execute(
        "SELECT id FROM categories ORDER BY sort_order DESC LIMIT 1"
    ).fetchone()["id"]
    response = client.patch(
        f"/api/members/{member_id}", json={"category_id": other}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["category_id"] == other


def test_self_can_delete_own_account(client, make_member):
    member_id, headers = make_member("철수")
    deleted = client.delete(f"/api/members/{member_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/board").json()["members"] == []


def test_deleting_member_removes_schedules(client, make_member, conn):
    member_id, headers = make_member("철수")
    conn.execute(
        "INSERT INTO schedules"
        " (member_id, day_of_week, start_slot, end_slot, title, color)"
        " VALUES (?, 0, 6, 9, '수업', '#ef4444')",
        (member_id,),
    )
    client.delete(f"/api/members/{member_id}", headers=headers)
    assert client.get("/api/board").json()["schedules"] == []


def test_other_member_cannot_delete(client, make_member):
    target_id, _ = make_member("철수")
    _, other_headers = make_member("영희")
    response = client.delete(f"/api/members/{target_id}", headers=other_headers)
    assert response.status_code == 403


def test_admin_reorders_members(client, make_member, admin_headers, category_id):
    first_id, _ = make_member("가")
    second_id, _ = make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [second_id, first_id]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    order = [m["id"] for m in client.get("/api/board").json()["members"]]
    assert order == [second_id, first_id]


def test_member_cannot_reorder(client, make_member, category_id):
    first_id, headers = make_member("가")
    second_id, _ = make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [second_id, first_id]},
        headers=headers,
    )
    assert response.status_code == 403


def test_reorder_rejects_mismatched_ids(
    client, make_member, admin_headers, category_id
):
    first_id, _ = make_member("가")
    make_member("나")
    response = client.put(
        "/api/members/order",
        json={"category_id": category_id, "ordered_ids": [first_id]},
        headers=admin_headers,
    )
    assert response.status_code == 400
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_members.py -v
```

기대 출력: 대부분 404/405로 실패

- [ ] **Step 3: 입력 스키마 추가**

`backend/app/schemas.py` 상단 임포트를 아래로 바꾼다.

```python
from app.constants import MEMBER_PASSWORD_PATTERN, NAME_MAX_LEN
```

파일 끝에 추가한다.

```python
class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)
    category_id: int
    password: str = Field(pattern=MEMBER_PASSWORD_PATTERN)


class MemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LEN)
    password: str | None = Field(default=None, pattern=MEMBER_PASSWORD_PATTERN)
    category_id: int | None = None


class MemberOrderIn(BaseModel):
    category_id: int
    ordered_ids: list[int]
```

- [ ] **Step 4: 멤버 라우터 작성**

`backend/app/routers/members.py`:

```python
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
```

- [ ] **Step 5: main.py에 라우터 등록**

임포트에 `members`를 추가하고, `app.include_router(categories.router)` 아래에 추가한다.

```python
    app.include_router(members.router)
```

- [ ] **Step 6: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_members.py -v
```

기대 출력: `18 passed`

- [ ] **Step 7: 커밋**

```bash
git add backend/app backend/tests/test_members.py
git commit -m "feat: add member CRUD with per-field permissions"
```

---

### Task 8: 일정 API와 겹침 검증

**Files:**
- Create: `backend/app/routers/schedules.py`
- Modify: `backend/app/schemas.py` (입력 모델 추가)
- Modify: `backend/app/main.py` (라우터 등록)
- Test: `backend/tests/test_schedules.py`

**Interfaces:**
- Consumes: `app.timeslot.overlaps`, `app.timeslot.describe`, `app.auth.require_self_or_admin`, `app.constants.PALETTE`, `app.constants.SLOT_COUNT`, `app.constants.TITLE_MAX_LEN`
- Produces:
  - `app.schemas.ScheduleCreate` — `member_id, day_of_week, start_slot, end_slot, title, color`
  - `app.schemas.ScheduleUpdate` — `member_id`를 뺀 나머지 전부 optional
  - `POST /api/schedules`, `PATCH /api/schedules/{id}`, `DELETE /api/schedules/{id}`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_schedules.py`:

```python
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
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_schedules.py -v
```

기대 출력: 대부분 404/405로 실패

- [ ] **Step 3: 입력 스키마 추가**

`backend/app/schemas.py` 상단 임포트를 아래로 바꾼다.

```python
from pydantic import BaseModel, Field, model_validator

from app.constants import (
    MEMBER_PASSWORD_PATTERN,
    NAME_MAX_LEN,
    PALETTE,
    SLOT_COUNT,
    TITLE_MAX_LEN,
)
```

파일 끝에 추가한다.

```python
class ScheduleCreate(BaseModel):
    member_id: int
    day_of_week: int = Field(ge=0, le=6)
    start_slot: int = Field(ge=0, le=SLOT_COUNT - 1)
    end_slot: int = Field(ge=1, le=SLOT_COUNT)
    title: str = Field(min_length=1, max_length=TITLE_MAX_LEN)
    color: str

    @model_validator(mode="after")
    def _check(self) -> "ScheduleCreate":
        if self.start_slot >= self.end_slot:
            raise ValueError("종료 시간은 시작 시간보다 뒤여야 합니다.")
        if self.color not in PALETTE:
            raise ValueError("허용되지 않은 색상입니다.")
        return self


class ScheduleUpdate(BaseModel):
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_slot: int | None = Field(default=None, ge=0, le=SLOT_COUNT - 1)
    end_slot: int | None = Field(default=None, ge=1, le=SLOT_COUNT)
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LEN)
    color: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "ScheduleUpdate":
        if self.color is not None and self.color not in PALETTE:
            raise ValueError("허용되지 않은 색상입니다.")
        return self
```

`ScheduleUpdate`는 한쪽 슬롯만 보낼 수 있어 모델 단계에서 시작<종료를 검사할 수 없다. 라우터가 기존 값과 병합한 뒤 검사한다.

- [ ] **Step 4: 일정 라우터 작성**

`backend/app/routers/schedules.py`:

```python
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
```

- [ ] **Step 5: main.py에 라우터 등록**

임포트에 `schedules`를 추가하고, `app.include_router(members.router)` 아래에 추가한다.

```python
    app.include_router(schedules.router)
```

- [ ] **Step 6: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_schedules.py -v
```

기대 출력: `27 passed` (파라미터화된 검증 테스트 9개 포함)

- [ ] **Step 7: 백엔드 전체 테스트로 회귀를 확인**

```bash
.venv/Scripts/python -m pytest -v
```

기대 출력: `146 passed`

- [ ] **Step 8: 커밋**

```bash
git add backend/app backend/tests/test_schedules.py
git commit -m "feat: add schedule CRUD with overlap validation"
```

---

### Task 9: 프론트엔드 뼈대와 시간 변환 유틸

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/constants.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/utils/timeSlot.ts`
- Test: `frontend/tests/timeSlot.spec.ts`

**Interfaces:**
- Consumes: 없음 (프론트 첫 태스크). 값은 `backend/app/constants.py`와 일치해야 한다
- Produces:
  - `src/constants.ts`: `DAY_START_HOUR`, `SLOT_MINUTES`, `SLOT_COUNT`, `DAY_NAMES`, `PALETTE`, `TITLE_MAX_LEN`, `NAME_MAX_LEN`
  - `src/types.ts`: `Category`, `Member`, `Schedule`, `Board`, `Credentials`
  - `src/utils/timeSlot.ts`: `slotToTime(slot: number): string`, `timeToSlot(text: string): number`, `describeSchedule(day: number, start: number, end: number): string`, `slotOptions(): SlotOption[]`
  - `SlotOption` — `{ value: number; label: string }`

- [ ] **Step 1: 패키지 설정 파일 작성**

`frontend/package.json`:

```json
{
  "name": "club-schedule-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "pinia": "^2.2.0",
    "vue": "^3.5.0",
    "vuedraggable": "^4.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "vitest": "^2.1.0",
    "vue-tsc": "^2.1.0"
  }
}
```

`frontend/vite.config.ts`:

```ts
/// <reference types="vitest" />
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.spec.ts'],
  },
})
```

개발 중에는 Vite(5173)가 `/api` 요청을 FastAPI(8000)로 넘긴다. 배포 시에는 FastAPI가 빌드 결과를 직접 서빙하므로 프록시가 필요 없다.

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["vite/client"],
    "strict": true,
    "noUnusedLocals": true,
    "skipLibCheck": true,
    "noEmit": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "tests/**/*.ts"]
}
```

`frontend/index.html`:

```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>동아리 주간 시간표</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 2: 의존성 설치**

`frontend/` 디렉터리에서 실행한다.

```bash
npm install
```

기대 출력: `added NNN packages` 로 끝나고 `node_modules/`가 생긴다

- [ ] **Step 3: 실패하는 테스트 작성**

`frontend/tests/timeSlot.spec.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { SLOT_COUNT } from '@/constants'
import {
  describeSchedule,
  slotOptions,
  slotToTime,
  timeToSlot,
} from '@/utils/timeSlot'

describe('slotToTime', () => {
  it('첫 슬롯은 하루 시작 시각이다', () => {
    expect(slotToTime(0)).toBe('06:00')
  })

  it('슬롯 6은 09:00이다', () => {
    expect(slotToTime(6)).toBe('09:00')
  })

  it('마지막 경계는 24:00이다', () => {
    expect(slotToTime(SLOT_COUNT)).toBe('24:00')
  })

  it('30분 단위를 표현한다', () => {
    expect(slotToTime(1)).toBe('06:30')
    expect(slotToTime(35)).toBe('23:30')
  })
})

describe('timeToSlot', () => {
  it('모든 슬롯을 왕복 변환한다', () => {
    for (let slot = 0; slot <= SLOT_COUNT; slot += 1) {
      expect(timeToSlot(slotToTime(slot))).toBe(slot)
    }
  })

  it('격자에 없는 시각을 거부한다', () => {
    expect(() => timeToSlot('09:15')).toThrow()
    expect(() => timeToSlot('05:30')).toThrow()
  })
})

describe('describeSchedule', () => {
  it('한 줄 문장으로 만든다', () => {
    expect(describeSchedule(0, 6, 14)).toBe('월 09:00~13:00')
    expect(describeSchedule(6, 0, 1)).toBe('일 06:00~06:30')
  })
})

describe('slotOptions', () => {
  it('0부터 마지막 경계까지 모두 준다', () => {
    const options = slotOptions()
    expect(options).toHaveLength(SLOT_COUNT + 1)
    expect(options[0]).toEqual({ value: 0, label: '06:00' })
    expect(options[SLOT_COUNT]).toEqual({ value: SLOT_COUNT, label: '24:00' })
  })
})
```

- [ ] **Step 4: 테스트를 실행해 실패를 확인**

```bash
npm test
```

기대 출력: `Failed to resolve import "@/constants"`

- [ ] **Step 5: 상수와 타입 작성**

`frontend/src/constants.ts`:

```ts
// backend/app/constants.py 와 값이 일치해야 한다.
export const DAY_START_HOUR = 6
export const SLOT_MINUTES = 30
export const SLOT_COUNT = 36 // 06:00 ~ 24:00

export const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'] as const

export const PALETTE = [
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#14b8a6',
  '#3b82f6',
  '#6366f1',
  '#a855f7',
  '#ec4899',
  '#78716c',
] as const

export const NAME_MAX_LEN = 20
export const TITLE_MAX_LEN = 30
```

`frontend/src/types.ts`:

```ts
export interface Category {
  id: number
  name: string
  sort_order: number
}

export interface Member {
  id: number
  name: string
  category_id: number
  sort_order: number
}

export interface Schedule {
  id: number
  member_id: number
  day_of_week: number
  start_slot: number
  end_slot: number
  title: string
  color: string
}

export interface Board {
  categories: Category[]
  members: Member[]
  schedules: Schedule[]
}

/** 요청에 실어 보낼 인증 정보. 둘 다 비어 있으면 익명이다. */
export interface Credentials {
  adminPassword?: string
  memberId?: number
  memberPassword?: string
}
```

- [ ] **Step 6: 시간 변환 유틸 작성**

`frontend/src/utils/timeSlot.ts`:

```ts
import { DAY_NAMES, DAY_START_HOUR, SLOT_COUNT, SLOT_MINUTES } from '@/constants'

export interface SlotOption {
  value: number
  label: string
}

/** 슬롯 번호를 "HH:MM"으로. SLOT_COUNT는 "24:00"이다. */
export function slotToTime(slot: number): string {
  if (slot < 0 || slot > SLOT_COUNT) {
    throw new RangeError(`슬롯 범위를 벗어났습니다: ${slot}`)
  }
  const minutes = DAY_START_HOUR * 60 + slot * SLOT_MINUTES
  const hh = String(Math.floor(minutes / 60)).padStart(2, '0')
  const mm = String(minutes % 60).padStart(2, '0')
  return `${hh}:${mm}`
}

/** "HH:MM"을 슬롯 번호로. 격자에 없는 시각은 거부한다. */
export function timeToSlot(text: string): number {
  const [hourText, minuteText] = text.split(':')
  const minutes = Number(hourText) * 60 + Number(minuteText)
  const offset = minutes - DAY_START_HOUR * 60
  if (offset < 0 || offset % SLOT_MINUTES !== 0) {
    throw new RangeError(`격자에 없는 시각입니다: ${text}`)
  }
  const slot = offset / SLOT_MINUTES
  if (slot > SLOT_COUNT) {
    throw new RangeError(`격자에 없는 시각입니다: ${text}`)
  }
  return slot
}

/** "월 09:00~13:00" — 목록과 툴팁에 쓰는 한 줄 설명. */
export function describeSchedule(day: number, start: number, end: number): string {
  return `${DAY_NAMES[day]} ${slotToTime(start)}~${slotToTime(end)}`
}

/** 시작·종료 드롭다운에 쓸 전체 선택지. */
export function slotOptions(): SlotOption[] {
  return Array.from({ length: SLOT_COUNT + 1 }, (_, slot) => ({
    value: slot,
    label: slotToTime(slot),
  }))
}
```

- [ ] **Step 7: 테스트를 실행해 통과를 확인**

```bash
npm test
```

기대 출력: `Test Files  1 passed`, `Tests  8 passed`

- [ ] **Step 8: 커밋**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src frontend/tests
git commit -m "feat: scaffold frontend with time slot utilities"
```

---

### Task 10: 격자 배치 계산 (순수 함수)

격자에서 "어느 열 몇 번째 행"을 정하는 규칙을 컴포넌트 밖으로 빼낸다. 4시간짜리 일정이 8칸을 차지하는 블록 하나로 병합되는 것이 여기서 결정되고, 브라우저 없이 검증된다.

**Files:**
- Create: `frontend/src/utils/gridLayout.ts`
- Test: `frontend/tests/gridLayout.spec.ts`

**Interfaces:**
- Consumes: `@/constants` (`DAY_NAMES`, `SLOT_COUNT`), `@/types` (`Member`, `Schedule`)
- Produces:
  - `HEADER_ROWS = 2`, `TIME_COLUMN = 1`
  - `GridColumn` — `{ day: number; member: Member; gridColumn: number }`
  - `DayHeader` — `{ day: number; label: string; gridColumnStart: number; span: number }`
  - `ScheduleBlock` — `{ schedule: Schedule; gridColumn: number; gridRowStart: number; gridRowEnd: number }`
  - `buildColumns(members: Member[]): GridColumn[]`
  - `buildDayHeaders(memberCount: number): DayHeader[]`
  - `buildBlocks(members: Member[], schedules: Schedule[]): ScheduleBlock[]`
  - `rowForSlot(slot: number): number`
  - `totalColumns(memberCount: number): number`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/tests/gridLayout.spec.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { DAY_NAMES, SLOT_COUNT } from '@/constants'
import {
  HEADER_ROWS,
  buildBlocks,
  buildColumns,
  buildDayHeaders,
  rowForSlot,
  totalColumns,
} from '@/utils/gridLayout'
import type { Member, Schedule } from '@/types'

function member(id: number, name: string, sortOrder = id): Member {
  return { id, name, category_id: 1, sort_order: sortOrder }
}

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return {
    id: 1,
    member_id: 1,
    day_of_week: 0,
    start_slot: 6,
    end_slot: 14,
    title: '전공수업',
    color: '#ef4444',
    ...overrides,
  }
}

const THREE = [member(1, '철수'), member(2, '영희'), member(3, '민수')]

describe('buildColumns', () => {
  it('요일마다 선택 인원만큼 열을 만든다', () => {
    expect(buildColumns(THREE)).toHaveLength(DAY_NAMES.length * 3)
  })

  it('첫 열은 시간축 바로 오른쪽이다', () => {
    expect(buildColumns(THREE)[0].gridColumn).toBe(2)
  })

  it('열은 요일 먼저, 그 안에서 멤버 순서로 늘어선다', () => {
    const columns = buildColumns(THREE)
    expect(columns[0]).toMatchObject({ day: 0, gridColumn: 2 })
    expect(columns[2]).toMatchObject({ day: 0, gridColumn: 4 })
    expect(columns[3]).toMatchObject({ day: 1, gridColumn: 5 })
  })

  it('멤버가 없으면 열도 없다', () => {
    expect(buildColumns([])).toEqual([])
  })
})

describe('buildDayHeaders', () => {
  it('요일마다 인원수만큼 칸을 병합한다', () => {
    const headers = buildDayHeaders(3)
    expect(headers).toHaveLength(7)
    expect(headers[0]).toEqual({
      day: 0,
      label: '월',
      gridColumnStart: 2,
      span: 3,
    })
    expect(headers[1].gridColumnStart).toBe(5)
  })

  it('멤버가 없으면 헤더도 없다', () => {
    expect(buildDayHeaders(0)).toEqual([])
  })
})

describe('rowForSlot', () => {
  it('첫 슬롯은 헤더 두 줄 다음이다', () => {
    expect(rowForSlot(0)).toBe(HEADER_ROWS + 1)
  })

  it('마지막 경계는 격자 끝이다', () => {
    expect(rowForSlot(SLOT_COUNT)).toBe(HEADER_ROWS + 1 + SLOT_COUNT)
  })
})

describe('totalColumns', () => {
  it('시간축 한 열을 더한다', () => {
    expect(totalColumns(3)).toBe(1 + 21)
    expect(totalColumns(0)).toBe(1)
  })
})

describe('buildBlocks', () => {
  it('일정 하나를 블록 하나로 만든다', () => {
    const blocks = buildBlocks(THREE, [schedule()])
    expect(blocks).toHaveLength(1)
  })

  it('4시간 일정은 8칸을 차지하는 블록 하나가 된다', () => {
    const [block] = buildBlocks(THREE, [schedule({ start_slot: 6, end_slot: 14 })])
    expect(block.gridRowEnd - block.gridRowStart).toBe(8)
    expect(block.gridRowStart).toBe(rowForSlot(6))
    expect(block.gridRowEnd).toBe(rowForSlot(14))
  })

  it('30분 일정도 블록 하나다', () => {
    const [block] = buildBlocks(THREE, [schedule({ start_slot: 0, end_slot: 1 })])
    expect(block.gridRowEnd - block.gridRowStart).toBe(1)
  })

  it('멤버와 요일에 맞는 열에 놓인다', () => {
    const [block] = buildBlocks(
      THREE,
      [schedule({ member_id: 2, day_of_week: 1 })],
    )
    expect(block.gridColumn).toBe(2 + 1 * 3 + 1)
  })

  it('선택되지 않은 멤버의 일정은 빠진다', () => {
    const blocks = buildBlocks([member(1, '철수')], [schedule({ member_id: 2 })])
    expect(blocks).toEqual([])
  })

  it('여러 일정을 모두 배치한다', () => {
    const blocks = buildBlocks(THREE, [
      schedule({ id: 1, member_id: 1, day_of_week: 0 }),
      schedule({ id: 2, member_id: 3, day_of_week: 4 }),
    ])
    expect(blocks.map((b) => b.schedule.id)).toEqual([1, 2])
  })
})
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
npm test
```

기대 출력: `Failed to resolve import "@/utils/gridLayout"`

- [ ] **Step 3: 격자 배치 모듈 작성**

`frontend/src/utils/gridLayout.ts`:

```ts
import { DAY_NAMES } from '@/constants'
import type { Member, Schedule } from '@/types'

/** 요일 줄과 이름 줄, 두 줄이 격자 위에 얹힌다. */
export const HEADER_ROWS = 2
/** 맨 왼쪽 시간축이 차지하는 열 번호. */
export const TIME_COLUMN = 1

export interface GridColumn {
  day: number
  member: Member
  gridColumn: number
}

export interface DayHeader {
  day: number
  label: string
  gridColumnStart: number
  span: number
}

export interface ScheduleBlock {
  schedule: Schedule
  gridColumn: number
  gridRowStart: number
  gridRowEnd: number
}

/** 슬롯 번호를 CSS grid-row 선 번호로. */
export function rowForSlot(slot: number): number {
  return HEADER_ROWS + 1 + slot
}

/** 시간축까지 포함한 전체 열 개수. */
export function totalColumns(memberCount: number): number {
  return TIME_COLUMN + DAY_NAMES.length * memberCount
}

/** 요일 바깥, 멤버 안쪽 순서로 열을 펼친다. */
export function buildColumns(members: Member[]): GridColumn[] {
  const columns: GridColumn[] = []
  DAY_NAMES.forEach((_, day) => {
    members.forEach((member, index) => {
      columns.push({
        day,
        member,
        gridColumn: TIME_COLUMN + 1 + day * members.length + index,
      })
    })
  })
  return columns
}

/** 요일 헤더는 그 요일의 멤버 열 전체를 덮는다. */
export function buildDayHeaders(memberCount: number): DayHeader[] {
  if (memberCount === 0) {
    return []
  }
  return DAY_NAMES.map((label, day) => ({
    day,
    label,
    gridColumnStart: TIME_COLUMN + 1 + day * memberCount,
    span: memberCount,
  }))
}

/**
 * 일정 하나를 블록 하나로 바꾼다.
 *
 * 몇 슬롯에 걸치든 블록은 하나다. 09:00~13:00 일정은 8칸 높이의
 * 세로로 긴 블록 하나가 되고, 제목은 그 안에 한 번만 쓰인다.
 */
export function buildBlocks(
  members: Member[],
  schedules: Schedule[],
): ScheduleBlock[] {
  const columnOf = new Map<string, number>()
  for (const column of buildColumns(members)) {
    columnOf.set(`${column.day}:${column.member.id}`, column.gridColumn)
  }

  const blocks: ScheduleBlock[] = []
  for (const schedule of schedules) {
    const gridColumn = columnOf.get(
      `${schedule.day_of_week}:${schedule.member_id}`,
    )
    if (gridColumn === undefined) {
      continue // 선택되지 않은 멤버의 일정
    }
    blocks.push({
      schedule,
      gridColumn,
      gridRowStart: rowForSlot(schedule.start_slot),
      gridRowEnd: rowForSlot(schedule.end_slot),
    })
  }
  return blocks
}
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인**

```bash
npm test
```

기대 출력: `Test Files  2 passed`, `Tests  22 passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/utils/gridLayout.ts frontend/tests/gridLayout.spec.ts
git commit -m "feat: add grid layout calculation for merged schedule blocks"
```

---

### Task 11: API 클라이언트

**Files:**
- Create: `frontend/src/api/client.ts`
- Test: `frontend/tests/client.spec.ts`

**Interfaces:**
- Consumes: `@/types` (`Board`, `Category`, `Credentials`, `Member`, `Schedule`)
- Produces:
  - `ApiError` — `Error` 하위, 속성 `status: number`. 네트워크 실패는 `status === 0`
  - `authHeaders(creds?: Credentials): Record<string, string>`
  - `request<T>(method: string, path: string, options?: { body?: unknown; creds?: Credentials }): Promise<T>`
  - `api` — 엔드포인트별 래퍼 객체 (`board`, `verify`, `createCategory`, `renameCategory`, `deleteCategory`, `reorderCategories`, `createMember`, `updateMember`, `deleteMember`, `reorderMembers`, `createSchedule`, `updateSchedule`, `deleteSchedule`)

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/tests/client.spec.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, authHeaders, request } from '@/api/client'

function stubFetch(status: number, body: unknown) {
  const text = body === null ? '' : JSON.stringify(body)
  const fake = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(text),
  })
  vi.stubGlobal('fetch', fake)
  return fake
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('authHeaders', () => {
  it('자격이 없으면 헤더도 없다', () => {
    expect(authHeaders()).toEqual({})
    expect(authHeaders({})).toEqual({})
  })

  it('멤버 자격을 헤더로 만든다', () => {
    expect(authHeaders({ memberId: 7, memberPassword: '1234' })).toEqual({
      'X-Member-Id': '7',
      'X-Member-Password': '1234',
    })
  })

  it('관리자 자격이 멤버 자격보다 우선한다', () => {
    const headers = authHeaders({
      adminPassword: 'secret',
      memberId: 7,
      memberPassword: '1234',
    })
    expect(headers).toEqual({ 'X-Admin-Password': 'secret' })
  })
})

describe('request', () => {
  it('JSON 본문을 돌려준다', async () => {
    stubFetch(200, { categories: [], members: [], schedules: [] })
    const board = await request('GET', '/api/board')
    expect(board).toEqual({ categories: [], members: [], schedules: [] })
  })

  it('204에는 본문이 없다', async () => {
    stubFetch(204, null)
    await expect(request('DELETE', '/api/schedules/1')).resolves.toBeUndefined()
  })

  it('본문이 있으면 Content-Type을 붙인다', async () => {
    const fake = stubFetch(201, { id: 1 })
    await request('POST', '/api/categories', { body: { name: '4학년' } })
    const [, init] = fake.mock.calls[0]
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe(JSON.stringify({ name: '4학년' }))
  })

  it('인증 헤더를 실어 보낸다', async () => {
    const fake = stubFetch(200, {})
    await request('PATCH', '/api/members/7', {
      body: { name: '철수' },
      creds: { memberId: 7, memberPassword: '1234' },
    })
    const [, init] = fake.mock.calls[0]
    expect(init.headers['X-Member-Id']).toBe('7')
  })

  it('서버 오류 메시지를 그대로 전한다', async () => {
    stubFetch(409, { detail: "월 09:00~13:00 '전공수업'과(와) 겹칩니다." })
    await expect(request('POST', '/api/schedules')).rejects.toMatchObject({
      status: 409,
      message: "월 09:00~13:00 '전공수업'과(와) 겹칩니다.",
    })
  })

  it('검증 오류의 첫 메시지를 꺼낸다', async () => {
    stubFetch(422, {
      detail: [{ msg: 'Value error, 허용되지 않은 색상입니다.', loc: ['body'] }],
    })
    await expect(request('POST', '/api/schedules')).rejects.toMatchObject({
      message: '허용되지 않은 색상입니다.',
    })
  })

  it('네트워크 실패는 status 0이다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(request('GET', '/api/board')).rejects.toMatchObject({
      status: 0,
    })
  })

  it('던지는 것은 ApiError다', async () => {
    stubFetch(403, { detail: '관리자만 할 수 있습니다.' })
    await expect(request('DELETE', '/api/categories/1')).rejects.toBeInstanceOf(
      ApiError,
    )
  })
})
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
npm test
```

기대 출력: `Failed to resolve import "@/api/client"`

- [ ] **Step 3: 클라이언트 작성**

`frontend/src/api/client.ts`:

```ts
import type { Board, Category, Credentials, Member, Schedule } from '@/types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** 관리자 자격이 있으면 그쪽만 보낸다. 서버도 관리자를 우선 판정한다. */
export function authHeaders(creds: Credentials = {}): Record<string, string> {
  if (creds.adminPassword) {
    return { 'X-Admin-Password': creds.adminPassword }
  }
  if (creds.memberId !== undefined && creds.memberPassword) {
    return {
      'X-Member-Id': String(creds.memberId),
      'X-Member-Password': creds.memberPassword,
    }
  }
  return {}
}

/** FastAPI의 detail은 문자열이거나 검증 오류 배열이다. */
function extractDetail(data: unknown, status: number): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown }
      if (typeof first?.msg === 'string') {
        return first.msg.replace(/^Value error,\s*/, '')
      }
    }
  }
  return `요청이 실패했습니다. (${status})`
}

export async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; creds?: Credentials } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders(options.creds) }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없습니다.')
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    throw new ApiError(response.status, extractDetail(data, response.status))
  }
  return data as T
}

type VerifyBody = { scope: 'admin' } | { scope: 'member'; member_id: number }

export const api = {
  board: () => request<Board>('GET', '/api/board'),

  verify: (body: VerifyBody, creds: Credentials) =>
    request<{ ok: boolean }>('POST', '/api/auth/verify', { body, creds }),

  createCategory: (name: string, creds: Credentials) =>
    request<Category>('POST', '/api/categories', { body: { name }, creds }),

  renameCategory: (id: number, name: string, creds: Credentials) =>
    request<Category>('PATCH', `/api/categories/${id}`, { body: { name }, creds }),

  deleteCategory: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/categories/${id}`, { creds }),

  reorderCategories: (orderedIds: number[], creds: Credentials) =>
    request<{ ok: boolean }>('PUT', '/api/categories/order', {
      body: { ordered_ids: orderedIds },
      creds,
    }),

  createMember: (
    body: { name: string; category_id: number; password: string },
  ) => request<Member>('POST', '/api/members', { body }),

  updateMember: (
    id: number,
    body: { name?: string; password?: string; category_id?: number },
    creds: Credentials,
  ) => request<Member>('PATCH', `/api/members/${id}`, { body, creds }),

  deleteMember: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/members/${id}`, { creds }),

  reorderMembers: (categoryId: number, orderedIds: number[], creds: Credentials) =>
    request<{ ok: boolean }>('PUT', '/api/members/order', {
      body: { category_id: categoryId, ordered_ids: orderedIds },
      creds,
    }),

  createSchedule: (
    body: Omit<Schedule, 'id'>,
    creds: Credentials,
  ) => request<Schedule>('POST', '/api/schedules', { body, creds }),

  updateSchedule: (
    id: number,
    body: Partial<Omit<Schedule, 'id' | 'member_id'>>,
    creds: Credentials,
  ) => request<Schedule>('PATCH', `/api/schedules/${id}`, { body, creds }),

  deleteSchedule: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/schedules/${id}`, { creds }),
}
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인**

```bash
npm test
```

기대 출력: `Test Files  3 passed`, `Tests  33 passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/api/client.ts frontend/tests/client.spec.ts
git commit -m "feat: add api client with auth headers and error mapping"
```

---

### Task 12: Pinia 스토어

**Files:**
- Create: `frontend/src/stores/board.ts`
- Test: `frontend/tests/board.spec.ts`

**Interfaces:**
- Consumes: `@/api/client` (`api`, `ApiError`), `@/types`
- Produces:
  - `orderMembers(categories: Category[], members: Member[]): Member[]` — 카테고리 순서 → 카테고리 내 순서로 평탄화
  - `useBoardStore()` — 상태 `categories, members, schedules, selectedIds, unlocked, adminPassword, activeMemberId, error, loading`
  - 게터: `isAdmin`, `sortedCategories`, `orderedMembers`, `membersOf(categoryId)`, `selectedMembers`, `visibleSchedules`, `schedulesOf(memberId)`, `canEdit(memberId)`, `credentialsFor(memberId?)`, `memberById(id)`
  - 액션: `fetchBoard()`, `toggleSelection(id)`, `selectAll()`, `clearSelection()`, `unlockMember(id, password)`, `unlockAdmin(password)`, `lockAll()`, `reportError(err)`, `persist()`, `restore()`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/tests/board.spec.ts`:

```ts
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { orderMembers, useBoardStore } from '@/stores/board'
import type { Category, Member, Schedule } from '@/types'

const CATEGORIES: Category[] = [
  { id: 10, name: '1학년', sort_order: 0 },
  { id: 20, name: '2학년', sort_order: 1 },
]

const MEMBERS: Member[] = [
  { id: 3, name: '민수', category_id: 20, sort_order: 0 },
  { id: 1, name: '철수', category_id: 10, sort_order: 1 },
  { id: 2, name: '영희', category_id: 10, sort_order: 0 },
]

const SCHEDULES: Schedule[] = [
  {
    id: 100,
    member_id: 1,
    day_of_week: 2,
    start_slot: 6,
    end_slot: 14,
    title: '전공수업',
    color: '#ef4444',
  },
  {
    id: 101,
    member_id: 1,
    day_of_week: 0,
    start_slot: 20,
    end_slot: 24,
    title: '알바',
    color: '#3b82f6',
  },
  {
    id: 102,
    member_id: 3,
    day_of_week: 0,
    start_slot: 6,
    end_slot: 8,
    title: '교양',
    color: '#22c55e',
  },
]

function seeded() {
  const store = useBoardStore()
  store.categories = CATEGORIES
  store.members = MEMBERS
  store.schedules = SCHEDULES
  return store
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('orderMembers', () => {
  it('카테고리 순서 다음에 카테고리 안 순서로 늘어놓는다', () => {
    const names = orderMembers(CATEGORIES, MEMBERS).map((m) => m.name)
    expect(names).toEqual(['영희', '철수', '민수'])
  })
})

describe('선택', () => {
  it('토글로 켜고 끈다', () => {
    const store = seeded()
    store.toggleSelection(1)
    expect(store.selectedIds).toEqual([1])
    store.toggleSelection(1)
    expect(store.selectedIds).toEqual([])
  })

  it('선택된 멤버는 표시 순서를 따른다', () => {
    const store = seeded()
    store.toggleSelection(3)
    store.toggleSelection(2)
    expect(store.selectedMembers.map((m) => m.name)).toEqual(['영희', '민수'])
  })

  it('선택된 사람의 일정만 보인다', () => {
    const store = seeded()
    store.toggleSelection(1)
    expect(store.visibleSchedules.map((s) => s.id)).toEqual([100, 101])
  })

  it('전체 선택과 해제', () => {
    const store = seeded()
    store.selectAll()
    expect(store.selectedIds).toHaveLength(3)
    store.clearSelection()
    expect(store.selectedIds).toEqual([])
  })
})

describe('권한', () => {
  it('잠금 해제한 본인만 편집할 수 있다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    expect(store.canEdit(1)).toBe(true)
    expect(store.canEdit(2)).toBe(false)
  })

  it('관리자는 전부 편집할 수 있다', () => {
    const store = seeded()
    store.adminPassword = 'secret'
    expect(store.canEdit(2)).toBe(true)
    expect(store.isAdmin).toBe(true)
  })

  it('자격 정보는 관리자를 우선한다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    store.adminPassword = 'secret'
    expect(store.credentialsFor(1)).toEqual({ adminPassword: 'secret' })
  })

  it('잠금 해제한 멤버의 자격을 만든다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    expect(store.credentialsFor(1)).toEqual({
      memberId: 1,
      memberPassword: '1234',
    })
  })

  it('아무 자격도 없으면 빈 객체다', () => {
    const store = seeded()
    expect(store.credentialsFor(1)).toEqual({})
  })
})

describe('내 일정 목록', () => {
  it('요일 다음 시작 시각 순으로 정렬한다', () => {
    const store = seeded()
    expect(store.schedulesOf(1).map((s) => s.id)).toEqual([101, 100])
  })
})

describe('저장과 복원', () => {
  it('선택과 잠금 상태를 브라우저에 남긴다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    store.adminPassword = 'secret'
    store.toggleSelection(1)

    setActivePinia(createPinia())
    const revived = useBoardStore()
    revived.restore()

    expect(revived.selectedIds).toEqual([1])
    expect(revived.unlocked).toEqual({ 1: '1234' })
    expect(revived.adminPassword).toBe('secret')
  })

  it('저장된 것이 없어도 문제없다', () => {
    const store = useBoardStore()
    store.restore()
    expect(store.selectedIds).toEqual([])
  })
})

describe('fetchBoard', () => {
  it('서버 응답을 상태에 넣는다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              categories: CATEGORIES,
              members: MEMBERS,
              schedules: SCHEDULES,
            }),
          ),
      }),
    )
    const store = useBoardStore()
    await store.fetchBoard()
    expect(store.members).toHaveLength(3)
    expect(store.error).toBe('')
    vi.unstubAllGlobals()
  })

  it('사라진 멤버의 선택과 잠금을 정리한다', async () => {
    const store = seeded()
    store.toggleSelection(1)
    store.unlocked = { 1: '1234' }
    store.activeMemberId = 1

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: () =>
          Promise.resolve(
            JSON.stringify({
              categories: CATEGORIES,
              members: [MEMBERS[0]],
              schedules: [],
            }),
          ),
      }),
    )
    await store.fetchBoard()
    expect(store.selectedIds).toEqual([])
    expect(store.unlocked).toEqual({})
    expect(store.activeMemberId).toBeNull()
    vi.unstubAllGlobals()
  })

  it('실패하면 오류 메시지를 남긴다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    const store = useBoardStore()
    await store.fetchBoard()
    expect(store.error).toBe('서버에 연결할 수 없습니다.')
    vi.unstubAllGlobals()
  })
})
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
npm test
```

기대 출력: `Failed to resolve import "@/stores/board"`

- [ ] **Step 3: 스토어 작성**

`frontend/src/stores/board.ts`:

```ts
import { defineStore } from 'pinia'
import { ApiError, api } from '@/api/client'
import type { Category, Credentials, Member, Schedule } from '@/types'

const STORAGE_KEY = 'club-schedule'

/** 카테고리 순서를 먼저, 그 안에서 멤버 순서를 따라 한 줄로 편다. */
export function orderMembers(
  categories: Category[],
  members: Member[],
): Member[] {
  const rank = new Map(categories.map((c) => [c.id, c.sort_order]))
  return [...members].sort(
    (a, b) =>
      (rank.get(a.category_id) ?? 0) - (rank.get(b.category_id) ?? 0) ||
      a.sort_order - b.sort_order ||
      a.id - b.id,
  )
}

interface BoardState {
  categories: Category[]
  members: Member[]
  schedules: Schedule[]
  selectedIds: number[]
  /** memberId -> 4자리 비밀번호. 잠금 해제한 사람만 들어 있다. */
  unlocked: Record<number, string>
  adminPassword: string
  /** "내 일정" 화면이 대상으로 삼는 멤버. */
  activeMemberId: number | null
  error: string
  loading: boolean
}

interface Persisted {
  selectedIds?: number[]
  unlocked?: Record<number, string>
  adminPassword?: string
  activeMemberId?: number | null
}

export const useBoardStore = defineStore('board', {
  state: (): BoardState => ({
    categories: [],
    members: [],
    schedules: [],
    selectedIds: [],
    unlocked: {},
    adminPassword: '',
    activeMemberId: null,
    error: '',
    loading: false,
  }),

  getters: {
    isAdmin: (state) => state.adminPassword !== '',

    sortedCategories: (state) =>
      [...state.categories].sort((a, b) => a.sort_order - b.sort_order),

    orderedMembers: (state) => orderMembers(state.categories, state.members),

    membersOf: (state) => (categoryId: number) =>
      state.members
        .filter((m) => m.category_id === categoryId)
        .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id),

    selectedMembers: (state) => {
      const chosen = new Set(state.selectedIds)
      return orderMembers(state.categories, state.members).filter((m) =>
        chosen.has(m.id),
      )
    },

    visibleSchedules: (state) => {
      const chosen = new Set(state.selectedIds)
      return state.schedules.filter((s) => chosen.has(s.member_id))
    },

    schedulesOf: (state) => (memberId: number) =>
      state.schedules
        .filter((s) => s.member_id === memberId)
        .sort(
          (a, b) =>
            a.day_of_week - b.day_of_week || a.start_slot - b.start_slot,
        ),

    canEdit: (state) => (memberId: number) =>
      state.adminPassword !== '' || state.unlocked[memberId] !== undefined,

    credentialsFor:
      (state) =>
      (memberId?: number): Credentials => {
        if (state.adminPassword) {
          return { adminPassword: state.adminPassword }
        }
        if (memberId !== undefined && state.unlocked[memberId]) {
          return { memberId, memberPassword: state.unlocked[memberId] }
        }
        return {}
      },

    memberById: (state) => (id: number) =>
      state.members.find((m) => m.id === id) ?? null,
  },

  actions: {
    async fetchBoard() {
      this.loading = true
      try {
        const board = await api.board()
        this.categories = board.categories
        this.members = board.members
        this.schedules = board.schedules
        this.pruneSelection()
        this.error = ''
      } catch (err) {
        this.reportError(err)
      } finally {
        this.loading = false
      }
    },

    /** 서버에서 사라진 멤버를 선택·잠금 목록에서 걷어낸다. */
    pruneSelection() {
      const alive = new Set(this.members.map((m) => m.id))
      this.selectedIds = this.selectedIds.filter((id) => alive.has(id))
      for (const key of Object.keys(this.unlocked)) {
        if (!alive.has(Number(key))) {
          delete this.unlocked[Number(key)]
        }
      }
      if (this.activeMemberId !== null && !alive.has(this.activeMemberId)) {
        this.activeMemberId = null
      }
      this.persist()
    },

    toggleSelection(id: number) {
      const at = this.selectedIds.indexOf(id)
      if (at >= 0) {
        this.selectedIds.splice(at, 1)
      } else {
        this.selectedIds.push(id)
      }
      this.persist()
    },

    selectAll() {
      this.selectedIds = this.members.map((m) => m.id)
      this.persist()
    },

    clearSelection() {
      this.selectedIds = []
      this.persist()
    },

    async unlockMember(id: number, password: string) {
      await api.verify(
        { scope: 'member', member_id: id },
        { memberId: id, memberPassword: password },
      )
      this.unlocked[id] = password
      this.activeMemberId = id
      if (!this.selectedIds.includes(id)) {
        this.selectedIds.push(id)
      }
      this.persist()
    },

    async unlockAdmin(password: string) {
      await api.verify({ scope: 'admin' }, { adminPassword: password })
      this.adminPassword = password
      this.persist()
    },

    lockAll() {
      this.unlocked = {}
      this.adminPassword = ''
      this.activeMemberId = null
      this.persist()
    },

    reportError(err: unknown) {
      this.error =
        err instanceof ApiError ? err.message : '알 수 없는 오류가 발생했습니다.'
    },

    persist() {
      const payload: Persisted = {
        selectedIds: this.selectedIds,
        unlocked: this.unlocked,
        adminPassword: this.adminPassword,
        activeMemberId: this.activeMemberId,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    },

    restore() {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        return
      }
      try {
        const saved = JSON.parse(raw) as Persisted
        this.selectedIds = saved.selectedIds ?? []
        this.unlocked = saved.unlocked ?? {}
        this.adminPassword = saved.adminPassword ?? ''
        this.activeMemberId = saved.activeMemberId ?? null
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    },
  },
})
```

- [ ] **Step 4: 테스트를 실행해 통과를 확인**

```bash
npm test
```

기대 출력: `Test Files  4 passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/stores/board.ts frontend/tests/board.spec.ts
git commit -m "feat: add pinia board store with selection and unlock state"
```

---

### Task 13: 앱 셸과 시간표 격자 (읽기 전용)

배치 계산은 Task 10에서 이미 검증했다. 여기서는 그 결과를 화면에 그리고, 실제 브라우저에서 눈으로 확인한다.

**Files:**
- Create: `frontend/src/main.ts`
- Create: `frontend/src/style.css`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/components/ScheduleGrid.vue`

**Interfaces:**
- Consumes: `@/stores/board`, `@/utils/gridLayout`, `@/utils/timeSlot`, `@/constants`
- Produces:
  - `ScheduleGrid` 컴포넌트 — props `{ members: Member[]; schedules: Schedule[] }`, emit `select(schedule: Schedule)`
  - CSS 변수 `--slot-height: 22px`, `--time-col: 56px`, `--line-soft`, `--line-strong`, `--surface`, `--text`

- [ ] **Step 1: 전역 스타일 작성**

`frontend/src/style.css`:

```css
:root {
  --slot-height: 22px;
  --time-col: 56px;
  --surface: #ffffff;
  --surface-alt: #f8fafc;
  --line-soft: #e5e7eb;
  --line-strong: #cbd5e1;
  --text: #1f2937;
  --muted: #6b7280;
  --accent: #2563eb;

  font-family: system-ui, "Malgun Gothic", sans-serif;
  color: var(--text);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--surface-alt);
}

button {
  font: inherit;
  cursor: pointer;
}
```

- [ ] **Step 2: 진입점 작성**

`frontend/src/main.ts`:

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'

createApp(App).use(createPinia()).mount('#app')
```

- [ ] **Step 3: 격자 컴포넌트 작성**

`frontend/src/components/ScheduleGrid.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { SLOT_COUNT } from '@/constants'
import type { Member, Schedule } from '@/types'
import {
  buildBlocks,
  buildColumns,
  buildDayHeaders,
  rowForSlot,
  totalColumns,
} from '@/utils/gridLayout'
import { describeSchedule, slotToTime } from '@/utils/timeSlot'

const props = defineProps<{ members: Member[]; schedules: Schedule[] }>()
const emit = defineEmits<{ select: [schedule: Schedule] }>()

const columns = computed(() => buildColumns(props.members))
const dayHeaders = computed(() => buildDayHeaders(props.members.length))
const blocks = computed(() => buildBlocks(props.members, props.schedules))
const slots = computed(() => Array.from({ length: SLOT_COUNT }, (_, i) => i))

const gridStyle = computed(() => ({
  gridTemplateColumns:
    `var(--time-col) repeat(${totalColumns(props.members.length) - 1},` +
    ' minmax(76px, 1fr))',
  gridTemplateRows: `28px 26px repeat(${SLOT_COUNT}, var(--slot-height))`,
}))

const bodyRows = computed(() => `${rowForSlot(0)} / ${rowForSlot(SLOT_COUNT)}`)

function tooltip(schedule: Schedule): string {
  const when = describeSchedule(
    schedule.day_of_week,
    schedule.start_slot,
    schedule.end_slot,
  )
  return `${when} ${schedule.title}`
}
</script>

<template>
  <p v-if="members.length === 0" class="empty">
    위에서 이름을 선택하면 시간표가 나타납니다.
  </p>

  <div v-else class="scroll">
    <div class="grid" :style="gridStyle">
      <div class="corner" />

      <div
        v-for="head in dayHeaders"
        :key="`day-${head.day}`"
        class="day-head"
        :style="{
          gridColumn: `${head.gridColumnStart} / span ${head.span}`,
          gridRow: 1,
        }"
      >
        {{ head.label }}
      </div>

      <div
        v-for="(column, index) in columns"
        :key="`name-${column.day}-${column.member.id}`"
        class="name-head"
        :class="{ 'day-start': index % members.length === 0 }"
        :style="{ gridColumn: column.gridColumn, gridRow: 2 }"
      >
        {{ column.member.name }}
      </div>

      <div
        v-for="slot in slots"
        :key="`time-${slot}`"
        class="time"
        :class="{ hour: slot % 2 === 0 }"
        :style="{ gridColumn: 1, gridRow: rowForSlot(slot) }"
      >
        {{ slotToTime(slot) }}
      </div>

      <div
        v-for="(column, index) in columns"
        :key="`bg-${column.day}-${column.member.id}`"
        class="column-bg"
        :class="{ 'day-start': index % members.length === 0 }"
        :style="{ gridColumn: column.gridColumn, gridRow: bodyRows }"
      />

      <button
        v-for="block in blocks"
        :key="block.schedule.id"
        type="button"
        class="block"
        :title="tooltip(block.schedule)"
        :style="{
          gridColumn: block.gridColumn,
          gridRow: `${block.gridRowStart} / ${block.gridRowEnd}`,
          backgroundColor: block.schedule.color,
        }"
        @click="emit('select', block.schedule)"
      >
        <span class="block-title">{{ block.schedule.title }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.empty {
  padding: 48px 0;
  text-align: center;
  color: var(--muted);
}

.scroll {
  overflow: auto;
  max-height: calc(100vh - 240px);
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: var(--surface);
}

.grid {
  display: grid;
  min-width: max-content;
}

.corner {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 4;
  grid-column: 1;
  grid-row: 1 / 3;
  background: var(--surface);
  border-right: 1px solid var(--line-strong);
  border-bottom: 1px solid var(--line-strong);
}

.day-head,
.name-head {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  font-size: 12px;
  white-space: nowrap;
}

.day-head {
  position: sticky;
  top: 0;
  z-index: 3;
  font-weight: 700;
  border-bottom: 1px solid var(--line-soft);
  border-left: 2px solid var(--line-strong);
}

.name-head {
  position: sticky;
  top: 28px;
  z-index: 3;
  color: var(--muted);
  border-bottom: 1px solid var(--line-strong);
}

.name-head.day-start,
.column-bg.day-start {
  border-left: 2px solid var(--line-strong);
}

.time {
  position: sticky;
  left: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 6px;
  background: var(--surface);
  border-right: 1px solid var(--line-strong);
  font-size: 10px;
  color: var(--muted);
}

.time.hour {
  color: var(--text);
  font-weight: 600;
}

/* 30분마다 옅은 선, 1시간마다 진한 선. 칸을 하나씩 만들지 않고 배경으로 그린다. */
.column-bg {
  border-right: 1px solid var(--line-soft);
  background-image:
    repeating-linear-gradient(
      to bottom,
      var(--line-strong) 0 1px,
      transparent 1px calc(var(--slot-height) * 2)
    ),
    repeating-linear-gradient(
      to bottom,
      var(--line-soft) 0 1px,
      transparent 1px var(--slot-height)
    );
}

/* 몇 칸을 차지하든 블록은 하나. 제목도 그 안에 한 번만 들어간다. */
.block {
  z-index: 1;
  margin: 1px;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: none;
  border-radius: 4px;
  color: #fff;
  text-shadow: 0 1px 1px rgb(0 0 0 / 25%);
}

.block-title {
  font-size: 12px;
  line-height: 1.25;
  text-align: center;
  overflow: hidden;
  word-break: break-all;
}
</style>
```

- [ ] **Step 4: 앱 셸 작성**

이 단계의 `App.vue`는 격자를 눈으로 확인하기 위한 최소 형태다. Task 14에서 멤버 패널로 교체된다.

`frontend/src/App.vue`:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import ScheduleGrid from '@/components/ScheduleGrid.vue'
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()

onMounted(async () => {
  store.restore()
  await store.fetchBoard()
})
</script>

<template>
  <main class="app">
    <h1>동아리 주간 시간표</h1>

    <div class="toolbar">
      <button type="button" @click="store.selectAll()">전체 보기</button>
      <button type="button" @click="store.clearSelection()">선택 해제</button>
      <span v-if="store.loading" class="muted">불러오는 중…</span>
    </div>

    <p v-if="store.error" class="error">{{ store.error }}</p>

    <ScheduleGrid
      :members="store.selectedMembers"
      :schedules="store.visibleSchedules"
    />
  </main>
</template>

<style scoped>
.app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
}

h1 {
  font-size: 20px;
  margin: 0 0 12px;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.muted {
  color: var(--muted);
  font-size: 13px;
}

.error {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}
</style>
```

- [ ] **Step 5: 백엔드를 띄우고 샘플 데이터를 넣는다**

`backend/`에서 서버를 실행한다.

```bash
ADMIN_PASSWORD=admin-secret DB_PATH=./data/dev.db .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

PowerShell이라면 아래처럼 환경변수를 먼저 설정한다.

```powershell
$env:ADMIN_PASSWORD='admin-secret'; $env:DB_PATH='./data/dev.db'
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

새 터미널에서 샘플 데이터를 넣는다.

```bash
curl -X POST localhost:8000/api/members -H "Content-Type: application/json" \
  -d '{"name":"철수","category_id":1,"password":"1234"}'
curl -X POST localhost:8000/api/members -H "Content-Type: application/json" \
  -d '{"name":"영희","category_id":1,"password":"1234"}'
curl -X POST localhost:8000/api/schedules -H "Content-Type: application/json" \
  -H "X-Member-Id: 1" -H "X-Member-Password: 1234" \
  -d '{"member_id":1,"day_of_week":0,"start_slot":6,"end_slot":14,"title":"전공수업","color":"#ef4444"}'
curl -X POST localhost:8000/api/schedules -H "Content-Type: application/json" \
  -H "X-Member-Id: 2" -H "X-Member-Password: 1234" \
  -d '{"member_id":2,"day_of_week":2,"start_slot":20,"end_slot":24,"title":"알바","color":"#3b82f6"}'
```

- [ ] **Step 6: 개발 서버를 띄우고 눈으로 확인한다**

`frontend/`에서 실행한다.

```bash
npm run dev
```

브라우저에서 `http://localhost:5173` 을 열고 "전체 보기"를 누른 뒤 아래를 확인한다.

- 가로에 월~일, 각 요일 아래 철수·영희 두 열이 있다
- 세로에 06:00부터 23:30까지 36줄이 있다
- 철수의 월요일 09:00~13:00 "전공수업"이 **8칸 높이의 블록 하나**로 그려지고 제목이 **한 번만** 보인다
- 아래로 스크롤해도 요일·이름 헤더가 붙어 있고, 오른쪽으로 스크롤해도 시간 열이 붙어 있다
- 블록에 마우스를 올리면 "월 09:00~13:00 전공수업" 툴팁이 뜬다

- [ ] **Step 7: 커밋**

```bash
git add frontend/src
git commit -m "feat: render weekly grid with merged schedule blocks"
```

---

### Task 14: 멤버 패널과 잠금 해제

**Files:**
- Create: `frontend/src/components/BaseDialog.vue`
- Create: `frontend/src/components/MemberPanel.vue`
- Create: `frontend/src/components/UnlockDialog.vue`
- Modify: `frontend/src/App.vue` (임시 버튼을 패널과 잠금 해제로 교체)

**Interfaces:**
- Consumes: `@/stores/board` (`sortedCategories`, `membersOf`, `toggleSelection`, `canEdit`, `unlockMember`, `unlockAdmin`, `lockAll`), `@/api/client` (`ApiError`)
- Produces:
  - `BaseDialog` — props `{ title: string }`, slot 기본, emit `close()`
  - `MemberPanel` — props 없음, 스토어를 직접 읽는다
  - `UnlockDialog` — props `{ mode: 'member' | 'admin' }`, emit `close()`

- [ ] **Step 1: 공용 모달 껍데기 작성**

`frontend/src/components/BaseDialog.vue`:

```vue
<script setup lang="ts">
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <header>
        <h2>{{ title }}</h2>
        <button type="button" class="x" aria-label="닫기" @click="emit('close')">
          ✕
        </button>
      </header>
      <div class="body">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(15 23 42 / 45%);
}

.dialog {
  width: min(460px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: var(--surface);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgb(0 0 0 / 25%);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line-soft);
}

h2 {
  margin: 0;
  font-size: 16px;
}

.x {
  border: none;
  background: none;
  font-size: 16px;
  color: var(--muted);
}

.body {
  padding: 16px;
}
</style>
```

- [ ] **Step 2: 멤버 패널 작성**

`frontend/src/components/MemberPanel.vue`:

```vue
<script setup lang="ts">
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
</script>

<template>
  <section class="panel">
    <div
      v-for="category in store.sortedCategories"
      :key="category.id"
      class="group"
    >
      <h3>{{ category.name }}</h3>
      <div class="chips">
        <button
          v-for="member in store.membersOf(category.id)"
          :key="member.id"
          type="button"
          class="chip"
          :class="{
            on: store.selectedIds.includes(member.id),
            mine: store.canEdit(member.id),
          }"
          @click="store.toggleSelection(member.id)"
        >
          {{ store.selectedIds.includes(member.id) ? '☑' : '☐' }}
          {{ member.name }}
        </button>
        <span v-if="store.membersOf(category.id).length === 0" class="empty">
          아직 등록된 이름이 없습니다
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 8px;
}

.group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

h3 {
  flex: 0 0 72px;
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--surface);
  font-size: 13px;
}

.chip.on {
  border-color: var(--accent);
  background: #eff6ff;
  color: var(--accent);
}

/* 내가 편집할 수 있는 이름은 밑줄로 구분한다. */
.chip.mine {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.empty {
  font-size: 13px;
  color: var(--muted);
}
</style>
```

- [ ] **Step 3: 잠금 해제 다이얼로그 작성**

`frontend/src/components/UnlockDialog.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ mode: 'member' | 'admin' }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const memberId = ref<number | null>(store.activeMemberId)
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  try {
    if (props.mode === 'admin') {
      await store.unlockAdmin(password.value)
    } else if (memberId.value === null) {
      message.value = '이름을 선택해 주세요.'
      return
    } else {
      await store.unlockMember(memberId.value, password.value)
    }
    emit('close')
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '확인에 실패했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog
    :title="mode === 'admin' ? '관리자 모드' : '내 이름 잠금 해제'"
    @close="emit('close')"
  >
    <form @submit.prevent="submit">
      <label v-if="mode === 'member'">
        이름
        <select v-model.number="memberId">
          <option :value="null" disabled>선택하세요</option>
          <option
            v-for="member in store.orderedMembers"
            :key="member.id"
            :value="member.id"
          >
            {{ member.name }}
          </option>
        </select>
      </label>

      <label>
        비밀번호
        <input
          v-model="password"
          :type="mode === 'admin' ? 'password' : 'text'"
          :inputmode="mode === 'admin' ? undefined : 'numeric'"
          :maxlength="mode === 'admin' ? undefined : 4"
          :placeholder="mode === 'admin' ? '관리자 비밀번호' : '숫자 4자리'"
          autocomplete="off"
        />
      </label>

      <p v-if="message" class="message">{{ message }}</p>

      <div class="actions">
        <button type="button" @click="emit('close')">취소</button>
        <button type="submit" class="primary" :disabled="busy">확인</button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}

input,
select {
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text);
}

.message {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.actions button {
  padding: 8px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
}

.actions .primary {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}
</style>
```

- [ ] **Step 4: 앱 셸에 붙이기**

`frontend/src/App.vue`의 `<script setup>` 을 아래로 바꾼다.

```ts
import { onMounted, ref } from 'vue'
import MemberPanel from '@/components/MemberPanel.vue'
import ScheduleGrid from '@/components/ScheduleGrid.vue'
import UnlockDialog from '@/components/UnlockDialog.vue'
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
const unlockMode = ref<'member' | 'admin' | null>(null)

onMounted(async () => {
  store.restore()
  await store.fetchBoard()
})
```

`<template>` 을 아래로 바꾼다.

```vue
<template>
  <main class="app">
    <h1>동아리 주간 시간표</h1>

    <div class="toolbar">
      <button type="button" @click="unlockMode = 'member'">
        내 이름 잠금 해제
      </button>
      <button type="button" @click="unlockMode = 'admin'">
        {{ store.isAdmin ? '관리자 모드 켜짐' : '관리자 모드' }}
      </button>
      <button
        v-if="store.isAdmin || Object.keys(store.unlocked).length > 0"
        type="button"
        @click="store.lockAll()"
      >
        잠그기
      </button>
      <span class="spacer" />
      <button type="button" @click="store.selectAll()">전체 보기</button>
      <button type="button" @click="store.clearSelection()">선택 해제</button>
    </div>

    <p v-if="store.error" class="error">{{ store.error }}</p>

    <MemberPanel />

    <ScheduleGrid
      :members="store.selectedMembers"
      :schedules="store.visibleSchedules"
    />

    <UnlockDialog
      v-if="unlockMode"
      :mode="unlockMode"
      @close="unlockMode = null"
    />
  </main>
</template>
```

`<style scoped>` 에 아래를 추가한다.

```css
.spacer {
  flex: 1;
}
```

- [ ] **Step 5: 브라우저에서 확인**

백엔드와 `npm run dev`를 띄운 상태에서 확인한다.

- 카테고리별로 이름 칩이 나오고 클릭하면 ☑ 로 바뀌며 시간표에 열이 추가된다
- "내 이름 잠금 해제"에서 철수 / 1234 를 넣으면 다이얼로그가 닫히고 철수 칩에 밑줄이 생긴다
- 틀린 비밀번호를 넣으면 "비밀번호가 틀렸습니다. (남은 시도 9회)"가 뜬다
- "관리자 모드"에 `admin-secret` 을 넣으면 버튼이 "관리자 모드 켜짐"으로 바뀐다
- 새로고침해도 선택과 잠금 해제 상태가 유지된다

- [ ] **Step 6: 테스트가 여전히 통과하는지 확인**

```bash
npm test
```

기대 출력: `Test Files  4 passed`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src
git commit -m "feat: add member panel and password unlock"
```

---

### Task 15: 이름 등록·수정·삭제

**Files:**
- Create: `frontend/src/components/MemberDialog.vue`
- Modify: `frontend/src/App.vue` (툴바에 버튼 추가)

**Interfaces:**
- Consumes: `@/api/client` (`api.createMember`, `api.updateMember`, `api.deleteMember`, `ApiError`), `@/stores/board` (`memberById`, `credentialsFor`, `isAdmin`, `unlockMember`, `fetchBoard`)
- Produces:
  - `MemberDialog` — props `{ mode: 'create' | 'edit'; memberId?: number }`, emit `close()`

- [ ] **Step 1: 다이얼로그 작성**

`frontend/src/components/MemberDialog.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { NAME_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ mode: 'create' | 'edit'; memberId?: number }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const target = computed(() =>
  props.memberId === undefined ? null : store.memberById(props.memberId),
)

const name = ref(target.value?.name ?? '')
const categoryId = ref<number>(
  target.value?.category_id ?? store.sortedCategories[0]?.id ?? 0,
)
const password = ref('')
const message = ref('')
const busy = ref(false)
const confirmingDelete = ref(false)

const title = computed(() =>
  props.mode === 'create' ? '이름 등록' : '이름 수정',
)

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청에 실패했습니다.'
}

async function create() {
  const created = await api.createMember({
    name: name.value.trim(),
    category_id: categoryId.value,
    password: password.value,
  })
  await store.fetchBoard()
  // 방금 만든 사람은 바로 자기 시간표를 쓸 수 있어야 한다.
  await store.unlockMember(created.id, password.value)
}

async function update() {
  const current = target.value
  if (current === null) {
    return
  }
  const body: { name?: string; password?: string; category_id?: number } = {}
  if (name.value.trim() !== current.name) {
    body.name = name.value.trim()
  }
  if (password.value) {
    body.password = password.value
  }
  if (store.isAdmin && categoryId.value !== current.category_id) {
    body.category_id = categoryId.value
  }
  if (Object.keys(body).length === 0) {
    return
  }
  await api.updateMember(current.id, body, store.credentialsFor(current.id))
  // 본인 자격으로 비밀번호를 바꿨다면 저장해 둔 값도 갱신해야 계속 편집할 수 있다.
  if (body.password && store.unlocked[current.id] !== undefined) {
    store.unlocked[current.id] = body.password
    store.persist()
  }
  await store.fetchBoard()
}

async function submit() {
  message.value = ''
  busy.value = true
  try {
    if (props.mode === 'create') {
      await create()
    } else {
      await update()
    }
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}

async function remove() {
  const current = target.value
  if (current === null) {
    return
  }
  message.value = ''
  busy.value = true
  try {
    await api.deleteMember(current.id, store.credentialsFor(current.id))
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog :title="title" @close="emit('close')">
    <form @submit.prevent="submit">
      <label>
        이름
        <input v-model="name" :maxlength="NAME_MAX_LEN" autocomplete="off" />
      </label>

      <label v-if="mode === 'create' || store.isAdmin">
        카테고리
        <select v-model.number="categoryId" :disabled="mode === 'edit' && !store.isAdmin">
          <option
            v-for="category in store.sortedCategories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <p v-else class="hint">
        소속 변경은 관리자에게 요청해 주세요.
      </p>

      <label>
        {{ mode === 'create' ? '비밀번호 (숫자 4자리)' : '새 비밀번호 (바꿀 때만)' }}
        <input
          v-model="password"
          inputmode="numeric"
          maxlength="4"
          placeholder="숫자 4자리"
          autocomplete="off"
        />
      </label>

      <p v-if="message" class="message">{{ message }}</p>

      <div v-if="confirmingDelete" class="confirm">
        <span>{{ target?.name }} 님의 이름과 일정을 모두 지웁니다.</span>
        <button type="button" @click="confirmingDelete = false">아니오</button>
        <button type="button" class="danger" :disabled="busy" @click="remove">
          삭제합니다
        </button>
      </div>

      <div class="actions">
        <button
          v-if="mode === 'edit' && !confirmingDelete"
          type="button"
          class="danger"
          @click="confirmingDelete = true"
        >
          삭제
        </button>
        <span class="spacer" />
        <button type="button" @click="emit('close')">취소</button>
        <button type="submit" class="primary" :disabled="busy">저장</button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}

input,
select {
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text);
}

.hint,
.message {
  margin: 0;
  font-size: 13px;
}

.hint {
  color: var(--muted);
}

.message {
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
}

.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #fef3c7;
  font-size: 13px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spacer {
  flex: 1;
}

.actions button,
.confirm button {
  padding: 8px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
}

.primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: #fff;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.confirm .danger {
  background: #dc2626 !important;
  color: #fff;
}
</style>
```

- [ ] **Step 2: 앱 셸에 붙이기**

`frontend/src/App.vue`의 `<script setup>` 에 아래를 추가한다.

```ts
import MemberDialog from '@/components/MemberDialog.vue'

const memberDialog = ref<{ mode: 'create' | 'edit'; memberId?: number } | null>(
  null,
)

function editableMemberIds(): number[] {
  return Object.keys(store.unlocked).map(Number)
}
```

툴바의 "내 이름 잠금 해제" 버튼 앞에 아래를 넣는다.

```vue
      <button type="button" @click="memberDialog = { mode: 'create' }">
        이름 등록
      </button>
      <button
        v-for="id in editableMemberIds()"
        :key="id"
        type="button"
        @click="memberDialog = { mode: 'edit', memberId: id }"
      >
        {{ store.memberById(id)?.name }} 정보
      </button>
```

`UnlockDialog` 아래에 추가한다.

```vue
    <MemberDialog
      v-if="memberDialog"
      :mode="memberDialog.mode"
      :member-id="memberDialog.memberId"
      @close="memberDialog = null"
    />
```

- [ ] **Step 3: 브라우저에서 확인**

- "이름 등록"으로 새 이름과 4자리 비밀번호를 넣으면 목록에 나타나고, 바로 잠금이 해제된 상태(밑줄)가 된다
- 같은 이름을 다시 등록하면 "이미 있는 이름입니다"가 뜬다
- 비밀번호에 3자리만 넣으면 서버가 거절하고 메시지가 보인다
- "<이름> 정보"에서 이름을 바꾸면 시간표 헤더의 이름도 바뀐다
- 관리자 모드가 아닐 때는 카테고리 선택 대신 "소속 변경은 관리자에게 요청해 주세요"가 보인다
- 관리자 모드를 켜면 카테고리를 바꿀 수 있고, 바꾸면 패널에서 다른 그룹으로 옮겨간다
- "삭제" → "삭제합니다"를 누르면 이름과 그 사람의 일정이 함께 사라진다

- [ ] **Step 4: 커밋**

```bash
git add frontend/src
git commit -m "feat: add member registration and profile editing"
```

---

### Task 16: 일정 추가·수정 폼

**Files:**
- Create: `frontend/src/components/ScheduleDialog.vue`
- Modify: `frontend/src/App.vue` (일정 추가 버튼, 격자 블록 클릭 연결)

**Interfaces:**
- Consumes: `@/api/client` (`api.createSchedule`, `api.updateSchedule`, `api.deleteSchedule`), `@/utils/timeSlot` (`slotOptions`), `@/constants` (`DAY_NAMES`, `PALETTE`, `SLOT_COUNT`, `TITLE_MAX_LEN`), `@/stores/board` (`canEdit`, `credentialsFor`)
- Produces:
  - `ScheduleDialog` — props `{ memberId: number; schedule?: Schedule }`, emit `close()`. `schedule`이 없으면 추가, 있으면 수정. 편집 권한이 없으면 읽기 전용으로 뜬다

- [ ] **Step 1: 다이얼로그 작성**

`frontend/src/components/ScheduleDialog.vue`:

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES, PALETTE, SLOT_COUNT, TITLE_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { slotOptions } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ memberId: number; schedule?: Schedule }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const readonly = computed(() => !store.canEdit(props.memberId))

const day = ref(props.schedule?.day_of_week ?? 0)
const start = ref(props.schedule?.start_slot ?? 6)
const end = ref(props.schedule?.end_slot ?? 8)
const title = ref(props.schedule?.title ?? '')
const color = ref<string>(props.schedule?.color ?? PALETTE[0])

const message = ref('')
const busy = ref(false)
const confirmingDelete = ref(false)

const startOptions = computed(() =>
  slotOptions().filter((option) => option.value < SLOT_COUNT),
)
const endOptions = computed(() =>
  slotOptions().filter((option) => option.value > start.value),
)

// 시작을 뒤로 옮기면 종료가 앞서지 않도록 함께 민다.
watch(start, (value) => {
  if (end.value <= value) {
    end.value = value + 1
  }
})

const heading = computed(() => {
  const owner = store.memberById(props.memberId)?.name ?? ''
  if (readonly.value) {
    return `${owner} 님의 일정`
  }
  return props.schedule ? '일정 수정' : '일정 추가'
})

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청에 실패했습니다.'
}

async function submit() {
  if (readonly.value) {
    return
  }
  message.value = ''
  busy.value = true
  const creds = store.credentialsFor(props.memberId)
  try {
    if (props.schedule) {
      await api.updateSchedule(
        props.schedule.id,
        {
          day_of_week: day.value,
          start_slot: start.value,
          end_slot: end.value,
          title: title.value.trim(),
          color: color.value,
        },
        creds,
      )
    } else {
      await api.createSchedule(
        {
          member_id: props.memberId,
          day_of_week: day.value,
          start_slot: start.value,
          end_slot: end.value,
          title: title.value.trim(),
          color: color.value,
        },
        creds,
      )
    }
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!props.schedule) {
    return
  }
  message.value = ''
  busy.value = true
  try {
    await api.deleteSchedule(
      props.schedule.id,
      store.credentialsFor(props.memberId),
    )
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog :title="heading" @close="emit('close')">
    <form @submit.prevent="submit">
      <label>
        요일
        <select v-model.number="day" :disabled="readonly">
          <option v-for="(label, index) in DAY_NAMES" :key="label" :value="index">
            {{ label }}요일
          </option>
        </select>
      </label>

      <div class="row">
        <label>
          시작
          <select v-model.number="start" :disabled="readonly">
            <option
              v-for="option in startOptions"
              :key="`s-${option.value}`"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
        <label>
          종료
          <select v-model.number="end" :disabled="readonly">
            <option
              v-for="option in endOptions"
              :key="`e-${option.value}`"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <label>
        제목
        <input
          v-model="title"
          :maxlength="TITLE_MAX_LEN"
          :disabled="readonly"
          placeholder="전공수업, 알바 …"
          autocomplete="off"
        />
      </label>

      <div class="palette">
        <button
          v-for="swatch in PALETTE"
          :key="swatch"
          type="button"
          class="swatch"
          :class="{ on: color === swatch }"
          :style="{ backgroundColor: swatch }"
          :disabled="readonly"
          :aria-label="`색상 ${swatch}`"
          @click="color = swatch"
        />
      </div>

      <p v-if="message" class="message">{{ message }}</p>

      <div v-if="confirmingDelete" class="confirm">
        <span>이 일정을 지웁니다.</span>
        <button type="button" @click="confirmingDelete = false">아니오</button>
        <button type="button" class="danger" :disabled="busy" @click="remove">
          삭제합니다
        </button>
      </div>

      <div class="actions">
        <button
          v-if="schedule && !readonly && !confirmingDelete"
          type="button"
          class="danger"
          @click="confirmingDelete = true"
        >
          삭제
        </button>
        <span class="spacer" />
        <button type="button" @click="emit('close')">
          {{ readonly ? '닫기' : '취소' }}
        </button>
        <button
          v-if="!readonly"
          type="submit"
          class="primary"
          :disabled="busy"
        >
          저장
        </button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 12px;
}

.row label {
  flex: 1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}

input,
select {
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text);
}

.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.swatch {
  width: 28px;
  height: 28px;
  border: 2px solid transparent;
  border-radius: 6px;
}

.swatch.on {
  border-color: var(--text);
}

.message {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #fef3c7;
  font-size: 13px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spacer {
  flex: 1;
}

.actions button,
.confirm button {
  padding: 8px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
}

.primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: #fff;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.confirm .danger {
  background: #dc2626 !important;
  color: #fff;
}
</style>
```

- [ ] **Step 2: 앱 셸에 붙이기**

`frontend/src/App.vue`의 `<script setup>` 에 추가한다.

```ts
import ScheduleDialog from '@/components/ScheduleDialog.vue'
import type { Schedule } from '@/types'

const scheduleDialog = ref<{ memberId: number; schedule?: Schedule } | null>(
  null,
)

function openBlock(schedule: Schedule) {
  scheduleDialog.value = { memberId: schedule.member_id, schedule }
}

function openNewSchedule(memberId: number) {
  scheduleDialog.value = { memberId }
}
```

툴바의 "이름 등록" 버튼 뒤에 추가한다.

```vue
      <button
        v-for="id in editableMemberIds()"
        :key="`add-${id}`"
        type="button"
        @click="openNewSchedule(id)"
      >
        {{ store.memberById(id)?.name }} 일정 추가
      </button>
```

`ScheduleGrid` 에 이벤트를 연결한다.

```vue
    <ScheduleGrid
      :members="store.selectedMembers"
      :schedules="store.visibleSchedules"
      @select="openBlock"
    />
```

`MemberDialog` 아래에 추가한다.

```vue
    <ScheduleDialog
      v-if="scheduleDialog"
      :member-id="scheduleDialog.memberId"
      :schedule="scheduleDialog.schedule"
      @close="scheduleDialog = null"
    />
```

- [ ] **Step 3: 브라우저에서 확인**

- "<이름> 일정 추가"로 월요일 09:00~13:00 "전공수업"을 넣으면 격자에 8칸짜리 블록 하나가 생긴다
- 같은 사람 같은 요일에 겹치는 시간을 넣으면 "월 09:00~13:00 '전공수업'과(와) 겹칩니다"가 뜬다
- 끝시간과 같은 시각으로 시작하는 일정(13:00~15:00)은 정상 등록된다
- 시작을 종료보다 뒤로 고르면 종료가 자동으로 밀려 항상 시작 < 종료가 유지된다
- 블록을 클릭하면 그 일정이 수정 모드로 열리고, 삭제도 된다
- 잠금 해제하지 않은 다른 사람의 블록을 클릭하면 읽기 전용으로 뜨고 저장 버튼이 없다

- [ ] **Step 4: 커밋**

```bash
git add frontend/src
git commit -m "feat: add schedule create and edit dialog"
```

---

### Task 17: 내 일정 텍스트 목록

한 줄이 "무슨 요일 몇 시부터 몇 시까지 무슨 일정"이라는 문장이 되게 한다. 격자를 클릭하지 않고 여기서 일정을 모두 관리할 수 있다.

**Files:**
- Create: `frontend/src/components/MyScheduleList.vue`
- Modify: `frontend/src/App.vue` ("내 일정" 버튼으로 목록 열기, 목록에서 폼 열기)

**Interfaces:**
- Consumes: `@/stores/board` (`schedulesOf`, `orderedMembers`, `isAdmin`, `unlocked`, `activeMemberId`, `credentialsFor`), `@/api/client` (`api.deleteSchedule`), `@/utils/timeSlot` (`slotToTime`), `@/constants` (`DAY_NAMES`)
- Produces:
  - `MyScheduleList` — props 없음. emit `close()`, `create(memberId: number)`, `edit(schedule: Schedule)`

- [ ] **Step 1: 목록 컴포넌트 작성**

`frontend/src/components/MyScheduleList.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { slotToTime } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{
  close: []
  create: [memberId: number]
  edit: [schedule: Schedule]
}>()

const store = useBoardStore()

/** 관리자는 모두, 일반 사용자는 잠금 해제한 본인만 고를 수 있다. */
const editableIds = computed(() =>
  store.isAdmin
    ? store.orderedMembers.map((member) => member.id)
    : Object.keys(store.unlocked).map(Number),
)

const targetId = ref<number | null>(
  store.activeMemberId ?? editableIds.value[0] ?? null,
)

const rows = computed(() =>
  targetId.value === null ? [] : store.schedulesOf(targetId.value),
)

const pendingDelete = ref<number | null>(null)
const message = ref('')
const busy = ref(false)

async function remove(schedule: Schedule) {
  message.value = ''
  busy.value = true
  try {
    await api.deleteSchedule(
      schedule.id,
      store.credentialsFor(schedule.member_id),
    )
    await store.fetchBoard()
    pendingDelete.value = null
  } catch (err) {
    message.value =
      err instanceof ApiError ? err.message : '삭제하지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog title="내 일정" @close="emit('close')">
    <p v-if="editableIds.length === 0" class="hint">
      먼저 이름을 잠금 해제해 주세요.
    </p>

    <template v-else>
      <label v-if="editableIds.length > 1" class="picker">
        대상
        <select v-model.number="targetId">
          <option v-for="id in editableIds" :key="id" :value="id">
            {{ store.memberById(id)?.name }}
          </option>
        </select>
      </label>

      <p v-if="rows.length === 0" class="hint">
        아직 등록된 일정이 없습니다.
      </p>

      <ol v-else class="rows">
        <li v-for="row in rows" :key="row.id">
          <span class="day">{{ DAY_NAMES[row.day_of_week] }}</span>
          <span class="time">
            {{ slotToTime(row.start_slot) }} ~ {{ slotToTime(row.end_slot) }}
          </span>
          <span class="title">{{ row.title }}</span>

          <template v-if="pendingDelete === row.id">
            <button type="button" @click="pendingDelete = null">아니오</button>
            <button
              type="button"
              class="danger"
              :disabled="busy"
              @click="remove(row)"
            >
              지웁니다
            </button>
          </template>
          <template v-else>
            <button type="button" @click="emit('edit', row)">수정</button>
            <button
              type="button"
              class="danger"
              @click="pendingDelete = row.id"
            >
              삭제
            </button>
          </template>
        </li>
      </ol>

      <p v-if="message" class="message">{{ message }}</p>

      <div class="actions">
        <button
          v-if="targetId !== null"
          type="button"
          class="primary"
          @click="emit('create', targetId)"
        >
          + 일정 추가
        </button>
      </div>
    </template>
  </BaseDialog>
</template>

<style scoped>
.picker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--muted);
}

.picker select {
  padding: 6px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  color: var(--text);
}

.hint {
  margin: 8px 0;
  color: var(--muted);
  font-size: 13px;
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--surface-alt);
  font-size: 13px;
}

.day {
  flex: 0 0 20px;
  font-weight: 700;
}

.time {
  flex: 0 0 120px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rows button {
  padding: 4px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 5px;
  background: var(--surface);
  font-size: 12px;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.message {
  margin: 8px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.primary {
  padding: 8px 14px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
}
</style>
```

- [ ] **Step 2: 앱 셸에 붙이기**

`frontend/src/App.vue`의 `<script setup>` 에 추가한다.

```ts
import MyScheduleList from '@/components/MyScheduleList.vue'

const showMyList = ref(false)
```

Task 16에서 넣은 "<이름> 일정 추가" 버튼 묶음을 지우고, 그 자리에 아래 한 개를 넣는다.

```vue
      <button type="button" @click="showMyList = true">내 일정</button>
```

`ScheduleDialog` 위에 추가한다.

```vue
    <MyScheduleList
      v-if="showMyList"
      @close="showMyList = false"
      @create="openNewSchedule"
      @edit="openBlock"
    />
```

- [ ] **Step 3: 브라우저에서 확인**

- 잠금 해제 전에 "내 일정"을 열면 "먼저 이름을 잠금 해제해 주세요"가 보인다
- 잠금 해제 후에는 일정이 `월  09:00 ~ 13:00  전공수업  [수정] [삭제]` 형태의 텍스트 줄로 나열된다
- 요일 순, 같은 요일 안에서는 시작 시각 순으로 정렬된다
- "+ 일정 추가"를 누르면 폼이 그 사람 대상으로 열린다
- "수정"을 누르면 같은 폼이 그 일정 내용으로 채워져 열린다
- "삭제" → "지웁니다"를 누르면 줄이 사라지고 격자에서도 블록이 없어진다
- 관리자 모드를 켜면 대상 드롭다운에 모든 멤버가 나온다

- [ ] **Step 4: 커밋**

```bash
git add frontend/src
git commit -m "feat: add plain-text schedule list for editing"
```

---

### Task 18: 관리자 전용 드래그 재배치와 카테고리 관리

표의 배치를 바꾸는 조작이라 관리자 모드일 때만 드래그 핸들이 살아난다. 일반 사용자에게는 드래그 자체가 없다.

**Files:**
- Create: `frontend/src/vuedraggable.d.ts`
- Modify: `frontend/src/components/MemberPanel.vue` (드래그 지원 추가)
- Create: `frontend/src/components/CategoryEditor.vue`
- Modify: `frontend/src/App.vue` ("카테고리 관리" 버튼)

**Interfaces:**
- Consumes: `vuedraggable`, `@/api/client` (`api.updateMember`, `api.reorderMembers`, `api.createCategory`, `api.renameCategory`, `api.deleteCategory`, `api.reorderCategories`), `@/stores/board` (`isAdmin`, `credentialsFor`, `reportError`)
- Produces:
  - `MemberPanel` — 관리자 모드에서 멤버 칩을 끌어 순서·소속 변경
  - `CategoryEditor` — props 없음, emit `close()`

- [ ] **Step 1: vuedraggable 타입 선언 추가**

`vuedraggable` 4.x는 자바스크립트로만 배포되어 타입 정의가 없다. 선언이 없으면
`npm run build`의 `vue-tsc` 단계에서 임포트가 실패한다.

`frontend/src/vuedraggable.d.ts`:

```ts
declare module 'vuedraggable' {
  import type { DefineComponent } from 'vue'

  const draggable: DefineComponent<
    { list?: unknown[]; group?: unknown; itemKey?: string; disabled?: boolean },
    Record<string, unknown>,
    unknown
  >
  export default draggable
}
```

- [ ] **Step 2: 멤버 패널에 드래그를 붙인다**

`frontend/src/components/MemberPanel.vue` 전체를 아래로 바꾼다.

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import type { Member } from '@/types'

const store = useBoardStore()

/** 드래그는 배열을 직접 뒤집으므로 스토어가 아닌 사본 위에서 다룬다. */
const groups = ref<Record<number, Member[]>>({})
const saving = ref(false)

function rebuild() {
  const next: Record<number, Member[]> = {}
  for (const category of store.sortedCategories) {
    next[category.id] = store.membersOf(category.id)
  }
  groups.value = next
}

watch(
  () => [store.categories, store.members],
  rebuild,
  { immediate: true, deep: true },
)

/**
 * 드래그가 끝나면 소속을 먼저 모두 옮기고, 그다음 순서를 확정한다.
 * 순서 API는 그 카테고리의 전체 멤버 집합을 요구하므로 순서가 뒤바뀌면 안 된다.
 */
async function commitAll() {
  if (!store.isAdmin || saving.value) {
    return
  }
  saving.value = true
  const creds = store.credentialsFor()
  try {
    for (const category of store.sortedCategories) {
      for (const member of groups.value[category.id] ?? []) {
        if (member.category_id !== category.id) {
          await api.updateMember(member.id, { category_id: category.id }, creds)
        }
      }
    }
    for (const category of store.sortedCategories) {
      const ids = (groups.value[category.id] ?? []).map((m) => m.id)
      await api.reorderMembers(category.id, ids, creds)
    }
  } catch (err) {
    store.reportError(err)
  } finally {
    saving.value = false
    await store.fetchBoard()
  }
}
</script>

<template>
  <section class="panel">
    <p v-if="store.isAdmin" class="notice">
      관리자 모드입니다. 이름을 끌어 순서와 소속을 바꿀 수 있습니다.
    </p>

    <div
      v-for="category in store.sortedCategories"
      :key="category.id"
      class="group"
    >
      <h3>{{ category.name }}</h3>

      <draggable
        v-model="groups[category.id]"
        class="chips"
        group="members"
        item-key="id"
        :disabled="!store.isAdmin"
        @end="commitAll"
      >
        <template #item="{ element }">
          <button
            type="button"
            class="chip"
            :class="{
              on: store.selectedIds.includes(element.id),
              mine: store.canEdit(element.id),
              draggable: store.isAdmin,
            }"
            @click="store.toggleSelection(element.id)"
          >
            {{ store.selectedIds.includes(element.id) ? '☑' : '☐' }}
            {{ element.name }}
          </button>
        </template>
        <template #footer>
          <span v-if="(groups[category.id] ?? []).length === 0" class="empty">
            아직 등록된 이름이 없습니다
          </span>
        </template>
      </draggable>
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 8px;
}

.notice {
  margin: 0;
  font-size: 12px;
  color: var(--accent);
}

.group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

h3 {
  flex: 0 0 72px;
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
  min-height: 30px;
}

.chip {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--surface);
  font-size: 13px;
}

.chip.on {
  border-color: var(--accent);
  background: #eff6ff;
  color: var(--accent);
}

.chip.mine {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.chip.draggable {
  cursor: grab;
}

.empty {
  font-size: 13px;
  color: var(--muted);
}
</style>
```

- [ ] **Step 3: 여기까지 브라우저에서 확인**

- 관리자 모드가 꺼져 있으면 이름을 끌어도 아무 일이 없다
- 관리자 모드를 켜면 안내 문구가 뜨고, 같은 학년 안에서 순서를 바꾸면 시간표 열 순서도 따라 바뀐다
- 이름을 다른 학년으로 끌어다 놓으면 소속이 바뀌고 새로고침해도 유지된다

- [ ] **Step 4: 카테고리 편집기 작성**

`frontend/src/components/CategoryEditor.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { ApiError, api } from '@/api/client'
import { NAME_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Category } from '@/types'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const list = ref<Category[]>([])
const newName = ref('')
const message = ref('')
const busy = ref(false)
const pendingDelete = ref<number | null>(null)

watch(
  () => store.categories,
  () => {
    list.value = store.sortedCategories
  },
  { immediate: true, deep: true },
)

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청에 실패했습니다.'
}

async function run(work: () => Promise<void>) {
  message.value = ''
  busy.value = true
  try {
    await work()
    await store.fetchBoard()
  } catch (err) {
    fail(err)
    await store.fetchBoard()
  } finally {
    busy.value = false
  }
}

async function add() {
  const name = newName.value.trim()
  if (!name) {
    return
  }
  await run(async () => {
    await api.createCategory(name, store.credentialsFor())
    newName.value = ''
  })
}

async function rename(category: Category, value: string) {
  const name = value.trim()
  if (!name || name === category.name) {
    return
  }
  await run(async () => {
    await api.renameCategory(category.id, name, store.credentialsFor())
  })
}

async function remove(category: Category) {
  await run(async () => {
    await api.deleteCategory(category.id, store.credentialsFor())
    pendingDelete.value = null
  })
}

async function commitOrder() {
  await run(async () => {
    await api.reorderCategories(
      list.value.map((category) => category.id),
      store.credentialsFor(),
    )
  })
}
</script>

<template>
  <BaseDialog title="카테고리 관리" @close="emit('close')">
    <p v-if="!store.isAdmin" class="hint">
      관리자 모드에서만 바꿀 수 있습니다.
    </p>

    <template v-else>
      <draggable v-model="list" item-key="id" class="rows" @end="commitOrder">
        <template #item="{ element }">
          <li>
            <span class="grip" aria-hidden="true">⠿</span>
            <input
              :value="element.name"
              :maxlength="NAME_MAX_LEN"
              @change="rename(element, ($event.target as HTMLInputElement).value)"
            />
            <span class="count">
              {{ store.membersOf(element.id).length }}명
            </span>

            <template v-if="pendingDelete === element.id">
              <button type="button" @click="pendingDelete = null">아니오</button>
              <button
                type="button"
                class="danger"
                :disabled="busy"
                @click="remove(element)"
              >
                지웁니다
              </button>
            </template>
            <button
              v-else
              type="button"
              class="danger"
              @click="pendingDelete = element.id"
            >
              삭제
            </button>
          </li>
        </template>
      </draggable>

      <form class="add" @submit.prevent="add">
        <input
          v-model="newName"
          :maxlength="NAME_MAX_LEN"
          placeholder="새 카테고리 이름"
        />
        <button type="submit" class="primary" :disabled="busy">추가</button>
      </form>

      <p v-if="message" class="message">{{ message }}</p>
    </template>
  </BaseDialog>
</template>

<style scoped>
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--surface-alt);
  font-size: 13px;
}

.grip {
  cursor: grab;
  color: var(--muted);
}

.rows input,
.add input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text);
}

.count {
  flex: 0 0 auto;
  color: var(--muted);
}

.add {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.rows button,
.add button {
  padding: 6px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
  font-size: 12px;
}

.primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: #fff;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.message {
  margin: 12px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}
</style>
```

- [ ] **Step 5: 앱 셸에 붙이기**

`frontend/src/App.vue`의 `<script setup>` 에 추가한다.

```ts
import CategoryEditor from '@/components/CategoryEditor.vue'

const showCategories = ref(false)
```

툴바 맨 앞에 추가한다.

```vue
      <button type="button" @click="showCategories = true">
        카테고리 관리
      </button>
```

`MyScheduleList` 위에 추가한다.

```vue
    <CategoryEditor v-if="showCategories" @close="showCategories = false" />
```

- [ ] **Step 6: 브라우저에서 확인**

- 관리자 모드가 꺼진 상태로 "카테고리 관리"를 열면 "관리자 모드에서만 바꿀 수 있습니다"만 보인다
- 관리자 모드에서 "4학년"을 추가하면 목록 맨 아래와 멤버 패널에 나타난다
- 이름 칸을 고쳐 포커스를 옮기면 이름이 바뀐다
- 소속 멤버가 있는 카테고리를 지우려 하면 "소속된 멤버 N명을 먼저 옮겨 주세요"가 뜬다
- 빈 카테고리는 지워지고, 마지막 하나만 남으면 "카테고리는 최소 1개 있어야 합니다"가 뜬다
- 행을 끌어 순서를 바꾸면 멤버 패널의 그룹 순서와 시간표 열 순서가 함께 바뀐다

- [ ] **Step 7: 테스트가 여전히 통과하는지 확인**

```bash
npm test
```

기대 출력: `Test Files  4 passed`

- [ ] **Step 8: 커밋**

```bash
git add frontend/src
git commit -m "feat: add admin drag reordering and category management"
```

---

### Task 19: 동기화·오류 배너·배포

여러 명이 동시에 편집하므로 화면이 저절로 최신을 따라가야 한다. 마지막으로 프론트 빌드를 FastAPI가 서빙하게 만들어 컨테이너 하나로 배포한다.

**Files:**
- Create: `frontend/src/components/ErrorBanner.vue`
- Modify: `frontend/src/App.vue` (폴링, 오류 배너)
- Modify: `backend/app/main.py` (정적 파일 서빙)
- Create: `Dockerfile`
- Create: `README.md`

**Interfaces:**
- Consumes: `@/stores/board` (`error`, `fetchBoard`)
- Produces:
  - `ErrorBanner` — props 없음, 스토어의 `error`를 읽고 닫으면 비운다
  - `FRONTEND_DIST` 환경변수 — 빌드 결과 경로. 없으면 저장소 구조에서 추론한다

- [ ] **Step 1: 오류 배너 작성**

`frontend/src/components/ErrorBanner.vue`:

```vue
<script setup lang="ts">
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
</script>

<template>
  <div v-if="store.error" class="banner" role="alert">
    <span>{{ store.error }}</span>
    <button type="button" @click="store.error = ''">닫기</button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

button {
  border: 1px solid #991b1b;
  border-radius: 5px;
  background: none;
  color: inherit;
  padding: 2px 8px;
  font-size: 12px;
}
</style>
```

- [ ] **Step 2: 앱에 폴링을 넣는다**

`frontend/src/App.vue`의 `<script setup>` 에 추가한다.

```ts
import { computed, onMounted, onUnmounted } from 'vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const POLL_MS = 15_000
let timer: number | undefined

/** 입력 중인 내용이 날아가지 않도록 다이얼로그가 열려 있으면 갱신을 미룬다. */
const anyDialogOpen = computed(
  () =>
    unlockMode.value !== null ||
    memberDialog.value !== null ||
    scheduleDialog.value !== null ||
    showMyList.value ||
    showCategories.value,
)

function refreshIfIdle() {
  if (document.visibilityState !== 'visible' || anyDialogOpen.value) {
    return
  }
  void store.fetchBoard()
}

onMounted(() => {
  store.restore()
  void store.fetchBoard()
  timer = window.setInterval(refreshIfIdle, POLL_MS)
  document.addEventListener('visibilitychange', refreshIfIdle)
})

onUnmounted(() => {
  if (timer !== undefined) {
    window.clearInterval(timer)
  }
  document.removeEventListener('visibilitychange', refreshIfIdle)
})
```

기존 `onMounted` 블록은 위 것으로 대체된다. `onMounted`가 두 번 선언되지 않도록 앞의 것을 지운다.

`<template>` 에서 `<p v-if="store.error" ...>` 줄을 지우고 그 자리에 넣는다.

```vue
    <ErrorBanner />
```

`<style scoped>` 에서 `.error` 규칙을 지운다.

- [ ] **Step 3: FastAPI가 프론트 빌드를 서빙하게 한다**

`backend/app/main.py` 상단 임포트에 추가한다.

```python
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles
```

`create_app` 의 마지막 `app.include_router(schedules.router)` 아래, `return app` 위에 넣는다.

```python
    dist = _frontend_dist()
    if dist.is_dir():
        # API 라우터를 모두 등록한 뒤에 마운트해야 "/"가 API를 가리지 않는다.
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
```

임포트 바로 아래, `create_app` 위에 헬퍼를 추가한다.

```python
def _frontend_dist() -> Path:
    """빌드된 Vue 파일 위치. 배포에서는 FRONTEND_DIST로 지정한다."""
    override = os.environ.get("FRONTEND_DIST")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"
```

기본값의 `parents[2]`는 `backend/app/main.py` 기준으로 저장소 루트다. 도커
이미지에서는 구조가 달라지므로 `FRONTEND_DIST` 환경변수로 덮어쓴다.

- [ ] **Step 4: 백엔드 테스트로 회귀를 확인**

```bash
.venv/Scripts/python -m pytest -v
```

기대 출력: `146 passed` — `frontend/dist`가 아직 없으므로 마운트 분기는 건너뛴다

- [ ] **Step 5: 프론트를 빌드해 통합 동작을 확인**

`frontend/`에서 빌드한다.

```bash
npm run build
```

기대 출력: `dist/index.html` 을 포함한 빌드 결과

`backend/`에서 서버만 띄우고 8000 포트로 접속한다.

```powershell
$env:ADMIN_PASSWORD='admin-secret'; $env:DB_PATH='./data/dev.db'
.venv/Scripts/python -m uvicorn app.main:app --port 8000 --workers 1
```

`http://localhost:8000` 에서 Vite 없이 앱 전체가 뜨는지 확인한다.

- [ ] **Step 6: 동기화 확인**

브라우저 창 두 개로 `http://localhost:8000` 을 연다.

- 한쪽에서 일정을 추가하면 다른 쪽이 15초 안에 따라온다
- 다이얼로그를 열어 둔 창은 입력 중 내용이 사라지지 않는다
- 다른 탭에 갔다가 돌아오면 즉시 갱신된다
- 서버를 끄면 "서버에 연결할 수 없습니다." 배너가 뜨고, 다시 켜면 사라진다

- [ ] **Step 7: Dockerfile 작성**

`Dockerfile`:

```dockerfile
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
RUN pip install --no-cache-dir ./backend
COPY --from=web /web/dist ./frontend/dist

ENV DB_PATH=/data/schedule.db
ENV FRONTEND_DIST=/srv/frontend/dist
VOLUME ["/data"]
EXPOSE 8000

# 시도 제한 카운터가 프로세스 메모리에 있으므로 워커는 반드시 1개다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 8: 이미지 빌드와 실행 확인**

```bash
docker build -t club-schedule .
docker run --rm -p 8000:8000 -e ADMIN_PASSWORD=change-me -v club-data:/data club-schedule
```

`http://localhost:8000` 에서 앱이 뜨고, 컨테이너를 지웠다 다시 띄워도 데이터가 남아 있는지 확인한다.

- [ ] **Step 9: README 작성**

`README.md`:

```markdown
# 동아리 주간 시간표

동아리원이 각자 접속해 매주 반복되는 고정 일정(수업·알바·강의)을 등록하고,
여러 명의 시간표를 엑셀형 격자에 나란히 놓고 비교하는 웹 앱입니다.

날짜 개념이 없습니다. 다루는 정보는 "어느 요일 몇 시부터 몇 시까지 무슨 일정"뿐입니다.

## 쓰는 법

1. **이름 등록** — 본인 이름과 숫자 4자리 비밀번호를 정합니다
2. **내 일정** — 요일·시작·종료·제목을 골라 매주 반복되는 일정을 넣습니다
3. **이름 선택** — 보고 싶은 사람을 여러 명 고르면 요일마다 열이 나뉘어 나란히 보입니다

비밀번호는 본인 일정을 지키기 위한 것입니다. 관리자 비밀번호로는 모든 일정을
고칠 수 있고, 카테고리(학년) 관리와 이름 순서·소속 변경은 관리자만 할 수 있습니다.

## 개발

```bash
# 백엔드 (backend/)
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
$env:ADMIN_PASSWORD='admin-secret'
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 프론트엔드 (frontend/)
npm install
npm run dev      # http://localhost:5173, /api 요청은 8000으로 프록시
```

테스트:

```bash
cd backend  && .venv/Scripts/python -m pytest    # 146개
cd frontend && npm test
```

## 배포

```bash
docker build -t club-schedule .
docker run -d -p 8000:8000 -e ADMIN_PASSWORD='충분히 긴 비밀번호' \
  -v club-data:/data --restart unless-stopped club-schedule
```

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `ADMIN_PASSWORD` | (필수) | 관리자 비밀번호. 길이 제한 없음, 8자 이상 권장 |
| `DB_PATH` | `/data/schedule.db` | SQLite 파일 경로 |
| `FRONTEND_DIST` | `/srv/frontend/dist` | 빌드된 프론트 경로 |

uvicorn 워커는 **1개**여야 합니다. 비밀번호 시도 제한 카운터가 프로세스 메모리에
있어서, 워커가 여러 개면 제한이 워커 수만큼 느슨해집니다.
```

- [ ] **Step 10: 최종 커밋**

```bash
git add .
git commit -m "feat: add polling sync, static serving, docker image, and readme"
```

---

## 완료 조건

전부 끝나면 아래가 모두 참이어야 한다.

- `cd backend && .venv/Scripts/python -m pytest` → 146 passed
- `cd frontend && npm test` → 4개 파일 전부 통과
- `docker run` 한 번으로 앱이 뜨고, 브라우저 두 개가 15초 안에 서로의 변경을 본다
- 4자리 비밀번호로 본인 일정만 고칠 수 있고, 10회 틀리면 10분 잠긴다
- 카테고리와 이름 배치는 관리자 비밀번호 없이는 바뀌지 않는다
- 09:00~13:00 일정이 8칸짜리 블록 하나로 그려지고 제목이 한 번만 보인다
- 화면 어디에도 날짜가 없다

---

## 실행 중 계획에서 벗어난 점

계획대로 구현하다 실제로 막힌 지점들과, 그때 내린 결정을 남긴다.

### 1. 운영 앱을 모듈 수준에서 만들면 테스트가 환경변수에 묶인다

Task 4의 `app = _build_production_app()` 은 `from app.main import create_app` 만
해도 실행되어, 테스트가 `ADMIN_PASSWORD` 없이는 수집조차 되지 않았다.

→ `create_production_app()` 팩토리로 바꾸고 모듈 수준 인스턴스를 없앴다.
uvicorn 실행 명령이 `app.main:create_production_app --factory` 로 바뀐다.

### 2. sqlite 커넥션을 스레드 사이에서 공유해야 한다

FastAPI는 동기 핸들러를 스레드풀에서 돌리는데 sqlite3는 기본적으로 커넥션을
만든 스레드에서만 쓸 수 있어 `ProgrammingError` 가 났다.

→ `check_same_thread=False`. 이 파이썬의 `sqlite3.threadsafety` 가 3(serialized)
이라 SQLite가 내부에서 접근을 직렬화한다. `connect()` 가 시작할 때 이 값을
확인하고, 3 미만이면 명시적으로 거부한다.

### 3. HTTP 헤더에는 한글 비밀번호를 실을 수 없다

관리자 비밀번호는 길이·문자 제한이 없다고 정했는데, 한글을 헤더에 넣으면
`UnicodeEncodeError` 가 난다. 브라우저 `fetch` 도 같은 이유로 거부한다.

→ 클라이언트가 `encodeURIComponent` 로 감싸 보내고 서버가 `urllib.parse.unquote`
로 푼다 (`app.auth.read_password_header`). 한글 관리자 비밀번호 테스트를 추가했다.

### 4. 컴포넌트 태스크의 순서를 합쳤다

계획은 Task 13~19에서 `App.vue` 를 일곱 번 고쳐 가며 매번 브라우저로 확인하는
구성이었다. 이 환경에서는 단계마다 브라우저를 띄우는 대신, 컴포넌트를 모두 만든
뒤 `App.vue` 를 최종 형태로 한 번 쓰고 통합 확인했다. 각 컴포넌트를 쓸 때마다
`npm run build`(vue-tsc 타입 검사 포함)로 조기에 오류를 잡았다.

`MemberPanel` 도 Task 14의 단순 버전을 만들었다가 Task 18에서 교체하는 대신
처음부터 드래그 지원 버전으로 만들었다.

### 5. 테스트 개수

계획에 적어 둔 기대값 중 Task 3은 13개가 아니라 12개였다. 다른 값은 3번 변경으로
테스트가 하나 늘면서 결과적으로 맞았다. 최종 개수는 백엔드 146개, 프론트 51개다.
