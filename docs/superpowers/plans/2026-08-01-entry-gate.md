# 사이트 입장 게이트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사이트 앞에 입장 비밀번호 한 겹을 두어 동아리원만 들어오게 하고, 관리자가 그 비밀번호와 첫 화면 문구를 사이트 안에서 고칠 수 있게 한다.

**Architecture:** `/api/*` 요청 전부를 미들웨어 한 겹으로 막는다. bcrypt 검증은 느려서 통과한 비밀번호의 SHA-256 지문만 메모리에 담아 두고 다음부터 건너뛴다. 문구와 해시는 새 테이블 없이 기존 `settings` 테이블에 담는다.

**Tech Stack:** 기존 그대로 — FastAPI / sqlite3 / bcrypt / pytest, Vue 3 / TypeScript / Pinia / Vitest

**Spec:** `docs/superpowers/specs/2026-08-01-entry-gate-design.md`

## Global Constraints

- **차단 범위**: `/api/` 로 시작하는 모든 경로. 예외는 `GET /api/gate` 와 `POST /api/gate/verify` 둘뿐이다. 정적 파일(`/`, `/assets/*`)은 막지 않는다
- **거부 응답**: `401` + 헤더 `X-Gate: required`. 개인 비밀번호가 틀린 `401` 과 구별해야 한다
- **`GATE_PASSWORD` 는 비어 있을 때만 세운다.** `ADMIN_PASSWORD` 는 매번 덮어쓰지만 입장 비밀번호는 관리자가 사이트에서 바꾸므로, 재시작할 때마다 환경변수 값으로 되돌아가면 안 된다
- **`GATE_PASSWORD` 가 없으면 서버가 시작을 거부한다** — 게이트 없이 배포되는 사고를 막는다
- **시도 제한은 `POST /api/gate/verify` 에만** 건다. 미들웨어에서 실패를 세면 비밀번호가 바뀐 걸 모르고 폴링하던 사람이 2분 반 만에 잠긴다
- **길이 제한**: 제목 1~40자, 설명 0~500자, 입장 비밀번호 4자 이상
- **비밀번호 헤더는 퍼센트 인코딩**으로 주고받는다. 기존 `X-Admin-Password` 와 같은 방식이다
- **브라우저에 저장하는 비밀번호는 입장 비밀번호 하나뿐이다.** 개인 4자리와 관리자 비밀번호는 계속 저장하지 않는다

## 파일 구조

```
backend/app/
  gate.py                 검증·캐시·문구 읽기 쓰기 (HTTP 를 모른다)
  routers/gate.py         GET · POST · PATCH /api/gate (HTTP 만 안다)
  main.py                 미들웨어 등록 — 통과 여부만 묻는다
  config.py               GATE_PASSWORD 읽기
backend/tests/
  conftest.py             게이트를 통과한 client, 통과 못 한 stranger
  test_gate.py            차단·통과·시도 제한·권한
frontend/src/
  api/client.ts           X-Gate-Password 부착, X-Gate 감지
  stores/board.ts         게이트 상태와 저장
  components/GateScreen.vue   첫 화면
  components/GateEditor.vue   관리자 수정
  App.vue                 통과 전후 분기
```

`gate.py` 는 검증과 캐시만, 라우터는 HTTP 만, 미들웨어는 통과 여부만 안다. 셋을 갈라 두면 캐시 방식을 바꿔도 라우터가 흔들리지 않는다.

---

### Task 1: 입장 설정과 검증기

**Files:**
- Create: `backend/app/gate.py`
- Create: `backend/tests/test_gate_keeper.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- Consumes: `app.auth.hash_password`, `app.auth.verify_password`, `app.db.get_setting`, `app.db.set_setting`
- Produces:
  - `app.gate.GATE_HASH_KEY`, `GATE_TITLE_KEY`, `GATE_INTRO_KEY` — settings 키 이름
  - `app.gate.DEFAULT_TITLE`, `DEFAULT_INTRO`, `TITLE_MAX_LEN`, `INTRO_MAX_LEN`, `MIN_GATE_PASSWORD_LEN`
  - `app.gate.GateKeeper()` — 메서드 `check(conn, raw) -> bool`, `reset() -> None`
  - `app.gate.read_gate(conn) -> dict[str, str]` (키 `title`, `intro`)
  - `app.gate.write_gate(conn, *, title=None, intro=None) -> None`
  - `app.gate.set_gate_password(conn, raw) -> None`
  - `app.gate.seed_gate(conn, password) -> None`
  - `app.config.Settings.gate_password: str`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_gate_keeper.py`:

```python
import pytest

from app.auth import hash_password
from app.db import connect, get_setting, initialize
from app.gate import (
    DEFAULT_INTRO,
    DEFAULT_TITLE,
    GATE_HASH_KEY,
    GateKeeper,
    read_gate,
    seed_gate,
    set_gate_password,
    write_gate,
)


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    initialize(connection, hash_password("admin"))
    yield connection
    connection.close()


def test_seed_sets_password_and_text(conn):
    seed_gate(conn, "club-gate")
    assert get_setting(conn, GATE_HASH_KEY) is not None
    assert read_gate(conn) == {"title": DEFAULT_TITLE, "intro": DEFAULT_INTRO}


def test_seed_does_not_overwrite_an_existing_password(conn):
    """관리자가 사이트에서 바꾼 비밀번호가 재시작 때 되돌아가면 안 된다."""
    seed_gate(conn, "first")
    set_gate_password(conn, "changed-by-admin")
    seed_gate(conn, "first")

    keeper = GateKeeper()
    assert keeper.check(conn, "changed-by-admin") is True
    assert keeper.check(conn, "first") is False


def test_keeper_accepts_the_right_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "club-gate") is True


def test_keeper_rejects_a_wrong_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "nope") is False


def test_keeper_rejects_an_empty_password(conn):
    seed_gate(conn, "club-gate")
    assert GateKeeper().check(conn, "") is False


def test_keeper_remembers_and_skips_the_slow_check(conn):
    """두 번째부터는 저장된 해시를 지워도 통과한다 — 기억으로 답했다는 뜻이다."""
    seed_gate(conn, "club-gate")
    keeper = GateKeeper()
    assert keeper.check(conn, "club-gate") is True

    conn.execute("DELETE FROM settings WHERE key = ?", (GATE_HASH_KEY,))
    assert keeper.check(conn, "club-gate") is True


def test_reset_forgets_everything(conn):
    seed_gate(conn, "club-gate")
    keeper = GateKeeper()
    keeper.check(conn, "club-gate")
    keeper.reset()

    conn.execute("DELETE FROM settings WHERE key = ?", (GATE_HASH_KEY,))
    assert keeper.check(conn, "club-gate") is False


def test_write_gate_changes_only_what_is_given(conn):
    seed_gate(conn, "club-gate")
    write_gate(conn, title="4thIS 시간표")
    assert read_gate(conn) == {"title": "4thIS 시간표", "intro": DEFAULT_INTRO}

    write_gate(conn, intro="문 앞에서 물어봅니다.")
    assert read_gate(conn) == {
        "title": "4thIS 시간표",
        "intro": "문 앞에서 물어봅니다.",
    }


def test_intro_can_be_emptied(conn):
    seed_gate(conn, "club-gate")
    write_gate(conn, intro="")
    assert read_gate(conn)["intro"] == ""
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_gate_keeper.py -q
```

기대 출력: `ModuleNotFoundError: No module named 'app.gate'`

- [ ] **Step 3: 게이트 모듈 작성**

`backend/app/gate.py`:

```python
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
```

- [ ] **Step 4: 설정에 GATE_PASSWORD 추가**

`backend/app/config.py` 전체를 아래로 바꾼다.

```python
"""환경변수에서 읽는 배포 설정."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    admin_password: str
    gate_password: str


def load_settings() -> Settings:
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        raise RuntimeError("환경변수 ADMIN_PASSWORD를 설정해 주세요.")
    # 게이트 없이 배포되는 사고를 막는다. 비어 있으면 아예 뜨지 않는다.
    gate_password = os.environ.get("GATE_PASSWORD", "")
    if not gate_password:
        raise RuntimeError("환경변수 GATE_PASSWORD를 설정해 주세요.")
    db_path = Path(os.environ.get("DB_PATH", "./data/schedule.db"))
    return Settings(
        db_path=db_path,
        admin_password=admin_password,
        gate_password=gate_password,
    )
```

- [ ] **Step 5: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_gate_keeper.py -q
```

기대 출력: `9 passed`

- [ ] **Step 6: 커밋**

```bash
git add backend/app/gate.py backend/app/config.py backend/tests/test_gate_keeper.py
git commit -m "feat: add entry gate settings and keeper"
```

---

### Task 2: 미들웨어로 API 막기

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_gate_wall.py`

**Interfaces:**
- Consumes: `app.gate.GateKeeper`, `app.gate.seed_gate`, `app.auth.read_password_header`
- Produces:
  - `app.main.create_app(conn, limiter, keeper: GateKeeper | None = None) -> FastAPI`
  - `app.state.gate` — 이 앱의 `GateKeeper`
  - 테스트 픽스처 `client` (게이트를 통과한 상태), `stranger` (헤더 없는 손님), `keeper`
  - `tests.conftest.GATE_PASSWORD` — `"club-gate"`

- [ ] **Step 1: 픽스처를 게이트에 맞게 고친다**

`backend/tests/conftest.py` 전체를 아래로 바꾼다. 기존 테스트 146개는 `client` 가
게이트 헤더를 자동으로 달아 주므로 그대로 통과한다.

```python
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.auth import AttemptLimiter, hash_password
from app.db import connect, initialize
from app.gate import GateKeeper, seed_gate
from app.main import create_app

ADMIN_PASSWORD = "admin-secret"
GATE_PASSWORD = "club-gate"


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
    seed_gate(connection, GATE_PASSWORD)
    yield connection
    connection.close()


@pytest.fixture
def limiter(clock):
    return AttemptLimiter(max_attempts=10, lockout_seconds=600, clock=clock)


@pytest.fixture
def keeper():
    return GateKeeper()


@pytest.fixture
def app(conn, limiter, keeper):
    return create_app(conn, limiter, keeper)


@pytest.fixture
def client(app):
    """게이트를 통과한 손님. 모든 요청에 입장 비밀번호가 붙는다."""
    with TestClient(app) as test_client:
        test_client.headers.update(
            {"X-Gate-Password": quote(GATE_PASSWORD, safe="")}
        )
        yield test_client


@pytest.fixture
def stranger(app):
    """입장 비밀번호를 모르는 손님."""
    with TestClient(app) as test_client:
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

- [ ] **Step 2: 벽이 서는지 확인하는 테스트 작성**

`backend/tests/test_gate_wall.py`:

```python
from urllib.parse import quote

from tests.conftest import GATE_PASSWORD


def test_stranger_cannot_read_the_board(stranger):
    response = stranger.get("/api/board")
    assert response.status_code == 401
    assert response.headers["X-Gate"] == "required"


def test_stranger_cannot_register_a_member(stranger, category_id):
    response = stranger.post(
        "/api/members",
        json={"name": "몰래", "category_id": category_id, "password": "1234"},
    )
    assert response.status_code == 401


def test_a_wrong_gate_password_is_refused(stranger):
    response = stranger.get(
        "/api/board", headers={"X-Gate-Password": quote("틀린값", safe="")}
    )
    assert response.status_code == 401
    assert response.headers["X-Gate"] == "required"


def test_the_right_gate_password_opens_the_api(client):
    assert client.get("/api/board").status_code == 200


def test_gate_text_is_readable_without_the_password(stranger):
    response = stranger.get("/api/gate")
    assert response.status_code == 200
    assert "title" in response.json()


def test_verify_is_reachable_without_the_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200


def test_a_refused_request_does_not_count_toward_the_lockout(stranger, limiter):
    """비밀번호가 바뀐 걸 모르고 폴링하던 사람이 잠기면 안 된다."""
    for _ in range(30):
        stranger.get("/api/board")

    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200
```

- [ ] **Step 3: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_gate_wall.py -q
```

기대 출력: 대부분 200 을 받아 실패한다 (아직 벽이 없다)

- [ ] **Step 4: 앱에 미들웨어를 세운다**

`backend/app/main.py` 전체를 아래로 바꾼다.

```python
"""FastAPI 앱 조립. 커넥션과 시도 제한기를 밖에서 주입받아 테스트가 쉽다."""

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import AttemptLimiter, hash_password, read_password_header
from app.config import load_settings
from app.db import connect, initialize
from app.errors import DomainError, TooManyAttempts
from app.gate import GateKeeper, seed_gate
from app.routers import auth as auth_router
from app.routers import board
from app.routers import categories
from app.routers import gate as gate_router
from app.routers import members
from app.routers import schedules

# 이 둘만 입장 비밀번호 없이 지난다.
# 첫 화면을 그리려면 문구가 필요하고, 비밀번호는 어딘가에서 확인해야 한다.
GATE_FREE = {("GET", "/api/gate"), ("POST", "/api/gate/verify")}


def _frontend_dist() -> Path:
    """빌드된 Vue 파일 위치. 배포에서는 FRONTEND_DIST로 지정한다.

    기본값의 parents[2]는 backend/app/main.py 기준으로 저장소 루트다.
    도커 이미지에서는 구조가 달라지므로 환경변수로 덮어쓴다.
    """
    override = os.environ.get("FRONTEND_DIST")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    conn: sqlite3.Connection,
    limiter: AttemptLimiter,
    keeper: GateKeeper | None = None,
) -> FastAPI:
    app = FastAPI(title="동아리 주간 시간표")
    app.state.conn = conn
    app.state.limiter = limiter
    app.state.gate = keeper or GateKeeper()

    @app.middleware("http")
    async def require_gate(request: Request, call_next):
        """데이터를 내주기 전에 입장 비밀번호를 묻는다.

        여기서는 통과 여부만 판정하고 실패를 세지 않는다. 관리자가 비밀번호를
        바꾼 걸 모르고 화면을 켜 둔 사람은 15초마다 실패하는데, 그것까지 세면
        2분 반 만에 잠긴다. 잠금은 사람이 직접 입력하는 곳에서만 센다.
        """
        path = request.url.path
        if path.startswith("/api/") and (request.method, path) not in GATE_FREE:
            raw = read_password_header(request, "X-Gate-Password") or ""
            if not request.app.state.gate.check(request.app.state.conn, raw):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "입장 비밀번호가 필요합니다."},
                    headers={"X-Gate": "required"},
                )
        return await call_next(request)

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
    app.include_router(auth_router.router)
    app.include_router(gate_router.router)
    app.include_router(categories.router)
    app.include_router(members.router)
    app.include_router(schedules.router)

    dist = _frontend_dist()
    if dist.is_dir():
        # API 라우터를 모두 등록한 뒤에 마운트해야 "/"가 API를 가리지 않는다.
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


def create_production_app() -> FastAPI:
    """운영용 앱. uvicorn은 --factory 로 이 함수를 부른다.

    모듈을 임포트하는 것만으로 DB를 열거나 ADMIN_PASSWORD를 요구하면
    테스트가 환경변수에 묶인다. 그래서 앱 생성은 호출 시점으로 미룬다.
    """
    settings = load_settings()
    conn = connect(settings.db_path)
    initialize(conn, hash_password(settings.admin_password))
    seed_gate(conn, settings.gate_password)
    return create_app(conn, AttemptLimiter())
```

- [ ] **Step 5: 라우터 자리를 비워 둔 채로는 뜨지 않는다**

Task 3에서 만들 `app/routers/gate.py` 가 아직 없어 임포트가 실패한다. 자리만 잡아 둔다.

`backend/app/routers/gate.py`:

```python
"""입장 게이트 API. 내용은 Task 3에서 채운다."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/gate")
```

- [ ] **Step 6: 벽 테스트를 실행해 통과를 확인**

`GET /api/gate` 와 `POST /api/gate/verify` 를 쓰는 두 테스트는 아직 라우터가 비어
404 로 실패한다. 나머지가 통과하면 벽은 선 것이다.

```bash
.venv/Scripts/python -m pytest tests/test_gate_wall.py -q
```

기대 출력: `2 failed, 5 passed` — 실패 두 개는 `/api/gate` 404

- [ ] **Step 7: 기존 테스트가 그대로 통과하는지 확인**

```bash
.venv/Scripts/python -m pytest tests/test_board.py tests/test_members.py tests/test_schedules.py tests/test_categories.py tests/test_actor.py -q
```

기대 출력: `78 passed` — 픽스처가 게이트 헤더를 달아 주므로 테스트 본문은 손댈 곳이 없다

- [ ] **Step 8: 커밋**

```bash
git add backend/app/main.py backend/app/routers/gate.py backend/tests
git commit -m "feat: require the entry password on every api call"
```

---

### Task 3: 게이트 API

**Files:**
- Modify: `backend/app/routers/gate.py` (Task 2에서 자리만 잡아 둔 파일)
- Modify: `backend/app/auth.py` (`_client_key` 를 공개로)
- Create: `backend/tests/test_gate_api.py`

**Interfaces:**
- Consumes: `app.gate.read_gate`, `write_gate`, `set_gate_password`, `GateKeeper`, `app.auth.require_admin`, `app.auth.resolve_actor`, `app.auth.client_key`, `app.auth.LockedOut`, `app.errors.Unauthorized`, `app.errors.TooManyAttempts`
- Produces:
  - `app.auth.client_key(request, target) -> str` (이름만 바뀐 기존 함수)
  - `GET /api/gate` → `{ title, intro }`
  - `POST /api/gate/verify` — body `{ password }`
  - `PATCH /api/gate` — body `{ title?, intro?, password? }`, 관리자 전용

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_gate_api.py`:

```python
from urllib.parse import quote

from app.gate import DEFAULT_INTRO, DEFAULT_TITLE
from tests.conftest import GATE_PASSWORD


def gate_headers(password: str) -> dict:
    return {"X-Gate-Password": quote(password, safe="")}


def test_read_returns_the_default_text(stranger):
    assert stranger.get("/api/gate").json() == {
        "title": DEFAULT_TITLE,
        "intro": DEFAULT_INTRO,
    }


def test_verify_accepts_the_right_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_verify_refuses_a_wrong_password(stranger):
    response = stranger.post("/api/gate/verify", json={"password": "nope"})
    assert response.status_code == 401


def test_verify_counts_down_the_remaining_tries(stranger):
    response = stranger.post("/api/gate/verify", json={"password": "nope"})
    assert "9" in response.json()["detail"]


def test_verify_locks_out_after_ten_tries(stranger):
    for _ in range(10):
        stranger.post("/api/gate/verify", json={"password": "nope"})
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 429


def test_lockout_expires(stranger, clock):
    for _ in range(10):
        stranger.post("/api/gate/verify", json={"password": "nope"})
    clock.advance(601)
    response = stranger.post("/api/gate/verify", json={"password": GATE_PASSWORD})
    assert response.status_code == 200


def test_only_an_admin_may_change_the_gate(client):
    assert client.patch("/api/gate", json={"title": "몰래"}).status_code == 403


def test_a_member_may_not_change_the_gate(client, make_member):
    _, headers = make_member("철수")
    response = client.patch("/api/gate", json={"title": "몰래"}, headers=headers)
    assert response.status_code == 403


def test_admin_changes_the_text(client, admin_headers, stranger):
    response = client.patch(
        "/api/gate",
        json={"title": "4thIS 시간표", "intro": "문 앞에서 물어봅니다."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert stranger.get("/api/gate").json() == {
        "title": "4thIS 시간표",
        "intro": "문 앞에서 물어봅니다.",
    }


def test_admin_changes_the_password(client, admin_headers, stranger):
    client.patch("/api/gate", json={"password": "new-gate-word"}, headers=admin_headers)

    # 옛 비밀번호로는 더 못 들어온다 — 기억도 함께 지워져야 한다.
    assert stranger.get("/api/board", headers=gate_headers(GATE_PASSWORD)).status_code == 401
    assert stranger.get("/api/board", headers=gate_headers("new-gate-word")).status_code == 200


def test_a_blank_title_is_refused(client, admin_headers):
    response = client.patch("/api/gate", json={"title": ""}, headers=admin_headers)
    assert response.status_code == 422


def test_a_short_password_is_refused(client, admin_headers):
    response = client.patch("/api/gate", json={"password": "abc"}, headers=admin_headers)
    assert response.status_code == 422


def test_a_long_title_is_refused(client, admin_headers):
    response = client.patch(
        "/api/gate", json={"title": "가" * 41}, headers=admin_headers
    )
    assert response.status_code == 422


def test_the_intro_may_be_emptied(client, admin_headers, stranger):
    client.patch("/api/gate", json={"intro": ""}, headers=admin_headers)
    assert stranger.get("/api/gate").json()["intro"] == ""
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_gate_api.py -q
```

기대 출력: 대부분 404/405 로 실패

- [ ] **Step 3: 클라이언트 키 헬퍼를 공개로 바꾼다**

`backend/app/auth.py` 에서 이름만 바꾼다. 시도 제한 키를 만드는 방법이 두 곳에
흩어지면, 나중에 프록시 뒤에서 실제 IP 를 읽도록 고칠 때 한쪽을 놓친다.

`def _client_key(request: Request, target: str) -> str:` 를 아래로 바꾼다.

```python
def client_key(request: Request, target: str) -> str:
    """시도 제한을 세는 단위. 같은 곳에서 같은 대상을 두드린 횟수를 센다."""
    host = request.client.host if request.client else "unknown"
    return f"{host}:{target}"
```

같은 파일에서 부르는 곳도 바꾼다.

```python
    key = client_key(request, target)
```

- [ ] **Step 4: 게이트 라우터 작성**

`backend/app/routers/gate.py` 전체를 아래로 바꾼다.

```python
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
```

- [ ] **Step 5: 테스트를 실행해 통과를 확인**

```bash
.venv/Scripts/python -m pytest tests/test_gate_api.py tests/test_gate_wall.py -q
```

기대 출력: `21 passed`

- [ ] **Step 6: 백엔드 전체를 돌려 회귀가 없는지 확인**

```bash
.venv/Scripts/python -m pytest -q
```

기대 출력: `176 passed` — 기존 146 + 게이트 30

- [ ] **Step 7: 커밋**

```bash
git add backend/app backend/tests
git commit -m "feat: add gate api for reading, verifying, and editing"
```

---

### Task 4: 프론트 클라이언트와 게이트 상태

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/board.ts`
- Modify: `frontend/tests/client.spec.ts`
- Modify: `frontend/tests/board.spec.ts`

**Interfaces:**
- Consumes: `@/api/client` 의 기존 `request`, `ApiError`
- Produces:
  - `ApiError` 에 속성 `gateRequired: boolean` 추가 (기본 `false`)
  - `setGatePassword(value: string): void` — 이후 모든 요청에 붙는다
  - `api.gate()`, `api.verifyGate(password)`, `api.updateGate(body, creds)`
  - 스토어 상태 `gateOpen: boolean`, `gateTitle: string`, `gateIntro: string`, `gatePassword: string`
  - 스토어 액션 `loadGate()`, `enterGate(password)`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/tests/client.spec.ts` 의 `stubFetch` 를 아래로 바꾼다. 응답 헤더를 읽을
수 있어야 게이트 거부를 알아본다.

```ts
function stubFetch(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
) {
  const text = body === null ? '' : JSON.stringify(body)
  const fake = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => headers[name] ?? null },
    text: () => Promise.resolve(text),
  })
  vi.stubGlobal('fetch', fake)
  return fake
}
```

같은 파일 끝에 추가한다.

```ts
describe('입장 비밀번호', () => {
  afterEach(() => {
    setGatePassword('')
  })

  it('정해 두면 모든 요청에 붙는다', async () => {
    setGatePassword('club-gate')
    const fake = stubFetch(200, {})
    await request('GET', '/api/board')
    const [, init] = fake.mock.calls[0]
    expect(init.headers['X-Gate-Password']).toBe('club-gate')
  })

  it('비ASCII 비밀번호도 퍼센트 인코딩해 싣는다', async () => {
    setGatePassword('동아리비밀')
    const fake = stubFetch(200, {})
    await request('GET', '/api/board')
    const [, init] = fake.mock.calls[0]
    expect(init.headers['X-Gate-Password']).toBe(encodeURIComponent('동아리비밀'))
  })

  it('정해 두지 않으면 헤더가 없다', async () => {
    const fake = stubFetch(200, {})
    await request('GET', '/api/board')
    const [, init] = fake.mock.calls[0]
    expect(init.headers['X-Gate-Password']).toBeUndefined()
  })

  it('X-Gate 가 붙은 401 은 게이트 오류로 갈린다', async () => {
    stubFetch(401, { detail: '입장 비밀번호가 필요합니다.' }, { 'X-Gate': 'required' })
    await expect(request('GET', '/api/board')).rejects.toMatchObject({
      status: 401,
      gateRequired: true,
    })
  })

  it('그냥 401 은 보통 오류다', async () => {
    stubFetch(401, { detail: '비밀번호가 틀렸습니다.' })
    await expect(request('POST', '/api/auth/verify')).rejects.toMatchObject({
      gateRequired: false,
    })
  })
})
```

파일 맨 위 임포트도 바꾼다.

```ts
import { ApiError, authHeaders, request, setGatePassword } from '@/api/client'
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인**

```bash
npm test
```

기대 출력: `setGatePassword` 를 찾지 못해 실패

- [ ] **Step 3: 클라이언트에 게이트를 붙인다**

`frontend/src/api/client.ts` 의 `ApiError` 와 `request` 를 아래로 바꾸고, 파일
맨 아래 `api` 객체에 세 줄을 더한다.

```ts
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** 입장 비밀번호가 없거나 틀려서 막힌 경우. 첫 화면으로 돌려보낸다. */
    public gateRequired = false,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 입장 비밀번호. 모든 요청에 실린다.
 *
 * 자격 증명과 달리 요청마다 넘겨받지 않고 여기 둔다 — 호출하는 쪽 전부가
 * 이 값을 알 필요는 없고, 사이트에 들어와 있는 동안은 늘 같기 때문이다.
 */
let gatePassword = ''

export function setGatePassword(value: string): void {
  gatePassword = value
}
```

`request` 안의 헤더 조립과 오류 처리를 바꾼다.

```ts
  const headers: Record<string, string> = { ...authHeaders(options.creds) }
  if (gatePassword) {
    headers['X-Gate-Password'] = encodeURIComponent(gatePassword)
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
```

```ts
  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    const gateRequired = response.headers.get('X-Gate') === 'required'
    throw new ApiError(
      response.status,
      extractDetail(data, response.status),
      gateRequired,
    )
  }
  return data as T
```

`api` 객체에 추가한다.

```ts
  gate: () => request<{ title: string; intro: string }>('GET', '/api/gate'),

  verifyGate: (password: string) =>
    request<{ ok: boolean }>('POST', '/api/gate/verify', { body: { password } }),

  updateGate: (
    body: { title?: string; intro?: string; password?: string },
    creds: Credentials,
  ) => request<{ title: string; intro: string }>('PATCH', '/api/gate', { body, creds }),
```

- [ ] **Step 4: 스토어 테스트 작성**

`frontend/tests/board.spec.ts` 끝에 추가한다.

```ts
describe('입장 게이트', () => {
  it('입장 비밀번호는 브라우저에 남는다', () => {
    const store = seeded()
    store.gatePassword = 'club-gate'
    store.persist()

    setActivePinia(createPinia())
    const revived = useBoardStore()
    revived.restore()

    expect(revived.gatePassword).toBe('club-gate')
  })

  it('저장된 비밀번호가 있으면 문을 지난 것으로 시작한다', () => {
    const store = seeded()
    store.gatePassword = 'club-gate'
    store.persist()

    setActivePinia(createPinia())
    const revived = useBoardStore()
    revived.restore()

    expect(revived.gateOpen).toBe(true)
  })

  it('저장된 비밀번호가 없으면 문 앞에서 시작한다', () => {
    const store = useBoardStore()
    store.restore()
    expect(store.gateOpen).toBe(false)
  })

  it('게이트에 막히면 문 앞으로 돌아가고 비밀번호를 버린다', async () => {
    const store = seeded()
    store.gatePassword = 'stale'
    store.gateOpen = true

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        headers: { get: (name: string) => (name === 'X-Gate' ? 'required' : null) },
        text: () => Promise.resolve(JSON.stringify({ detail: '입장 비밀번호가 필요합니다.' })),
      }),
    )
    await store.fetchBoard()

    expect(store.gateOpen).toBe(false)
    expect(store.gatePassword).toBe('')
    expect(store.error).toBe('')
    vi.unstubAllGlobals()
  })
})
```

마지막 검사가 `error` 를 비워 두는 이유는, 첫 화면으로 돌아가는 것이 이미 설명이라
그 위에 빨간 띠까지 띄우면 시끄럽기 때문이다.

- [ ] **Step 5: 스토어에 게이트 상태를 넣는다**

`frontend/src/stores/board.ts` 를 고친다. 임포트에 추가한다.

```ts
import { ApiError, api, setGatePassword } from '@/api/client'
import { DEFAULT_GATE_INTRO, DEFAULT_GATE_TITLE } from '@/constants'
```

`BoardState` 에 추가한다.

```ts
  /** 입장 비밀번호를 넣고 사이트 안에 들어와 있는지. */
  gateOpen: boolean
  gateTitle: string
  gateIntro: string
  /** 유일하게 브라우저에 남기는 비밀번호. 개인·관리자 것은 남기지 않는다. */
  gatePassword: string
```

`Persisted` 에 추가한다.

```ts
  gatePassword?: string
```

`state()` 에 추가한다.

```ts
    gateOpen: false,
    gateTitle: DEFAULT_GATE_TITLE,
    gateIntro: DEFAULT_GATE_INTRO,
    gatePassword: '',
```

`actions` 에 추가한다.

```ts
    async loadGate() {
      try {
        const gate = await api.gate()
        this.gateTitle = gate.title
        this.gateIntro = gate.intro
      } catch {
        // 문구를 못 받아도 첫 화면은 기본 문구로 뜬다.
      }
    },

    async enterGate(password: string) {
      await api.verifyGate(password)
      this.gatePassword = password
      setGatePassword(password)
      this.gateOpen = true
      this.persist()
    },
```

`fetchBoard` 의 `catch` 를 바꾼다.

```ts
      } catch (err) {
        if (err instanceof ApiError && err.gateRequired) {
          // 문 앞으로 돌아가는 것이 이미 설명이다. 빨간 띠까지 띄우지 않는다.
          this.gateOpen = false
          this.gatePassword = ''
          setGatePassword('')
          this.error = ''
          this.persist()
          return
        }
        this.reportError(err)
      } finally {
```

`persist` 를 바꾼다.

```ts
      const payload: Persisted = {
        selectedIds: this.selectedIds,
        colorMode: this.colorMode,
        gatePassword: this.gatePassword,
      }
```

`restore` 를 바꾼다.

```ts
        const saved = JSON.parse(raw) as Persisted
        this.selectedIds = saved.selectedIds ?? []
        this.colorMode = saved.colorMode ?? 'own'
        this.gatePassword = saved.gatePassword ?? ''
        setGatePassword(this.gatePassword)
        // 저장된 비밀번호가 맞는지는 첫 요청이 알려 준다. 맞으면 화면이
        // 깜빡이지 않고, 틀리면 그때 문 앞으로 돌아간다.
        this.gateOpen = this.gatePassword !== ''
```

- [ ] **Step 6: 기본 문구 상수를 더한다**

`frontend/src/constants.ts` 끝에 추가한다. 서버의 `app/gate.py` 와 같은 문구여야
첫 화면이 서버 응답을 기다리는 동안 글자가 바뀌지 않는다.

```ts
// backend/app/gate.py 의 DEFAULT_TITLE · DEFAULT_INTRO 와 같아야 한다.
export const DEFAULT_GATE_TITLE = '동아리 주간 시간표'
export const DEFAULT_GATE_INTRO =
  '동아리원만 볼 수 있습니다. 받은 비밀번호를 넣어 주세요.'
```

- [ ] **Step 7: 테스트를 실행해 통과를 확인**

```bash
npm test
```

기대 출력: `Tests  91 passed`

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/api/client.ts frontend/src/stores/board.ts frontend/src/constants.ts frontend/tests
git commit -m "feat: carry the entry password on every request"
```

---

### Task 5: 첫 화면

**Files:**
- Create: `frontend/src/components/GateScreen.vue`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: 스토어의 `gateTitle`, `gateIntro`, `gateOpen`, `enterGate`, `loadGate`, `fetchBoard`
- Produces: `GateScreen` 컴포넌트 — props 없음, 스토어를 직접 읽는다

- [ ] **Step 1: 첫 화면 작성**

`frontend/src/components/GateScreen.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  try {
    await store.enterGate(password.value)
    await store.fetchBoard()
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '들어가지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="gate">
    <div class="card">
      <h1>{{ store.gateTitle }}</h1>
      <p v-if="store.gateIntro" class="intro">{{ store.gateIntro }}</p>

      <form @submit.prevent="submit">
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="비밀번호"
          autocomplete="current-password"
          aria-label="입장 비밀번호"
        />
        <button type="submit" class="btn btn--primary" :disabled="busy">
          들어가기
        </button>
      </form>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>
    </div>
  </main>
</template>

<style scoped>
.gate {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* 표가 없는 화면이라 여백을 넉넉히 두고 제목을 세운다. */
.card {
  width: min(420px, 100%);
  padding: 36px 32px 32px;
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: 10px;
}

h1 {
  margin: 0 0 14px;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.3;
}

/* 관리자가 넣은 줄바꿈을 그대로 살린다. */
.intro {
  margin: 0 0 24px;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--mute);
  white-space: pre-line;
}

form {
  display: flex;
  gap: 8px;
}

form .input {
  flex: 1;
}

form .btn {
  flex: 0 0 auto;
}

.notice {
  margin-top: 14px;
}
</style>
```

- [ ] **Step 2: 앱을 문 앞과 안쪽으로 가른다**

`frontend/src/App.vue` 의 임포트에 추가한다.

```ts
import GateScreen from '@/components/GateScreen.vue'
```

`onMounted` 를 아래로 바꾼다.

```ts
onMounted(() => {
  store.restore()
  void store.loadGate()
  // 저장된 비밀번호가 맞으면 첫 화면이 깜빡이지 않는다. 틀리면 스토어가
  // 게이트 오류를 알아보고 문 앞으로 돌려보낸다.
  if (store.gateOpen) {
    void store.fetchBoard()
  }
  timer = window.setInterval(refreshIfIdle, POLL_MS)
  document.addEventListener('visibilitychange', refreshIfIdle)
})
```

`refreshIfIdle` 을 아래로 바꾼다.

```ts
function refreshIfIdle() {
  if (!store.gateOpen || document.visibilityState !== 'visible' || anyDialogOpen.value) {
    return
  }
  void store.fetchBoard()
}
```

`<template>` 맨 바깥을 아래로 감싼다. 기존 `<div class="shell">` 은 그대로 두고
앞에 한 줄, 뒤에 닫는 태그만 더한다.

```vue
<template>
  <GateScreen v-if="!store.gateOpen" />

  <div v-else class="shell">
    ... 기존 내용 그대로 ...
  </div>
</template>
```

- [ ] **Step 3: 브라우저에서 확인**

`backend/` 에서 서버를 띄운다.

```powershell
$env:ADMIN_PASSWORD='admin-secret'; $env:GATE_PASSWORD='club-gate'; $env:DB_PATH='./data/dev.db'
.venv/Scripts/python -m uvicorn app.main:create_production_app --factory --port 8000
```

`frontend/` 에서 `npm run dev` 후 확인한다.

- 처음 열면 제목·설명·비밀번호 칸만 있는 화면이 뜬다
- 아무 비밀번호나 넣으면 "비밀번호가 맞지 않습니다. (남은 시도 9회)"
- `club-gate` 를 넣으면 시간표로 들어간다
- 새로고침해도 첫 화면이 다시 뜨지 않는다
- 개발자 도구에서 `localStorage` 를 지우고 새로고침하면 다시 첫 화면이 뜬다

- [ ] **Step 4: 커밋**

```bash
git add frontend/src
git commit -m "feat: add the entry screen"
```

---

### Task 6: 관리자의 입장 설정

**Files:**
- Create: `frontend/src/components/GateEditor.vue`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `api.updateGate`, 스토어의 `credentialsFor`, `isAdmin`, `loadGate`, `gateTitle`, `gateIntro`
- Produces: `GateEditor` 컴포넌트 — emit `close()`

- [ ] **Step 1: 편집 다이얼로그 작성**

`frontend/src/components/GateEditor.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const title = ref(store.gateTitle)
const intro = ref(store.gateIntro)
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  const body: { title?: string; intro?: string; password?: string } = {}
  if (title.value.trim() !== store.gateTitle) {
    body.title = title.value.trim()
  }
  if (intro.value !== store.gateIntro) {
    body.intro = intro.value
  }
  if (password.value) {
    body.password = password.value
  }
  try {
    if (Object.keys(body).length > 0) {
      await api.updateGate(body, store.credentialsFor())
      await store.loadGate()
      // 내가 바꾼 비밀번호로 계속 머물러야 한다. 안 그러면 저장하자마자
      // 내 요청이 막혀 문 앞으로 튕긴다.
      if (body.password) {
        await store.enterGate(body.password)
      }
    }
    emit('close')
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '저장하지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog title="입장 설정" wide @close="emit('close')">
    <p v-if="!store.isAdmin" class="notice notice--quiet">
      관리자만 바꿀 수 있습니다.
    </p>

    <form v-else class="stack" @submit.prevent="submit">
      <p class="notice notice--quiet">
        사이트에 들어올 때 보이는 화면입니다.
      </p>

      <label class="field">
        <span>제목</span>
        <input v-model="title" class="input" maxlength="40" autocomplete="off" />
      </label>

      <label class="field">
        <span>설명</span>
        <textarea v-model="intro" class="input intro" maxlength="500" rows="4" />
      </label>

      <label class="field">
        <span>새 입장 비밀번호</span>
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="바꿀 때만 채우세요 (4자 이상)"
          autocomplete="new-password"
        />
      </label>

      <p v-if="password" class="notice notice--warn">
        바꾸면 동아리원 모두가 다시 입력해야 합니다.
      </p>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <div class="row-end">
        <span class="spacer" />
        <button type="button" class="btn" @click="emit('close')">취소</button>
        <button type="submit" class="btn btn--primary" :disabled="busy">
          저장
        </button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
.intro {
  resize: vertical;
  line-height: 1.5;
  font-family: inherit;
}
</style>
```

- [ ] **Step 2: 관리자 버튼을 단다**

`frontend/src/App.vue` 의 임포트와 상태에 추가한다.

```ts
import GateEditor from '@/components/GateEditor.vue'

const showGate = ref(false)
```

`anyDialogOpen` 에 더한다.

```ts
const anyDialogOpen = computed(
  () =>
    unlockFor.value !== null ||
    memberDialog.value !== null ||
    scheduleDialog.value !== null ||
    showMyList.value ||
    showCategories.value ||
    showGate.value,
)
```

"카테고리" 버튼 바로 뒤에 넣는다.

```vue
      <button
        v-if="store.isAdmin"
        type="button"
        class="btn"
        @click="showGate = true"
      >
        입장 설정
      </button>
```

`CategoryEditor` 옆에 다이얼로그를 놓는다.

```vue
    <GateEditor v-if="showGate" @close="showGate = false" />
```

- [ ] **Step 3: 브라우저에서 확인**

- 관리자 모드가 꺼져 있으면 "입장 설정" 버튼이 보이지 않는다
- 관리자 모드에서 제목과 설명을 고치면, 로그아웃 후 첫 화면에 그대로 뜬다
- 설명에 줄바꿈을 넣으면 첫 화면에서도 줄이 나뉜다
- 새 비밀번호 칸을 채우면 "바꾸면 동아리원 모두가 다시 입력해야 합니다" 경고가 뜬다
- 비밀번호를 바꿔도 **내 화면은 튕기지 않는다** (바꾼 비밀번호로 이어서 머문다)
- 다른 브라우저(시크릿 창)에서는 옛 비밀번호가 막히고 첫 화면이 뜬다

- [ ] **Step 4: 프론트 빌드와 테스트**

```bash
npm run build
npm test
```

기대 출력: 빌드 성공, `Tests  91 passed`

- [ ] **Step 5: 커밋**

```bash
git add frontend/src
git commit -m "feat: let admins edit the entry screen and password"
```

---

### Task 7: 배포 준비

**Files:**
- Modify: `backend/run.ps1` (저장소에 올라가지 않는 로컬 실행 스크립트)
- Modify: `README.md`
- Modify: `Dockerfile` (주석만)

**Interfaces:**
- Consumes: `GATE_PASSWORD` 환경변수
- Produces: 배포 절차 문서

- [ ] **Step 1: 로컬 실행 스크립트에 게이트를 더한다**

`backend/run.ps1` 을 아래로 바꾼다. 이 파일은 `.gitignore` 에 있어 저장소에
올라가지 않는다.

```powershell
# 동아리 주간 시간표 — 로컬 실행
# 비밀번호가 들어 있어 저장소에 올리지 않는다 (.gitignore)
$env:ADMIN_PASSWORD = '4thIS_admin'
$env:GATE_PASSWORD = 'club-gate'
$env:DB_PATH = './data/schedule.db'
.\.venv\Scripts\python.exe -m uvicorn app.main:create_production_app --factory --host 0.0.0.0 --port 8000 --workers 1
```

- [ ] **Step 2: Dockerfile 에 주석을 더한다**

`Dockerfile` 의 `ENV DB_PATH=/data/schedule.db` 위에 넣는다. 비밀번호는 이미지에
굽지 않고 실행할 때 넘긴다.

```dockerfile
# ADMIN_PASSWORD 와 GATE_PASSWORD 는 이미지에 굽지 않는다.
# 배포처의 환경변수로 넘긴다 — 둘 다 없으면 서버가 시작을 거부한다.
```

- [ ] **Step 3: README 를 고친다**

`README.md` 의 환경변수 표를 아래로 바꾼다.

```markdown
| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `ADMIN_PASSWORD` | (필수) | 관리자 비밀번호. **띄울 때마다 덮어쓴다** |
| `GATE_PASSWORD` | (필수) | 사이트 입장 비밀번호. **처음 한 번만 세운다** — 이후에는 관리자가 사이트에서 바꾼다 |
| `DB_PATH` | `/data/schedule.db` | SQLite 파일 경로 |
| `FRONTEND_DIST` | `/srv/frontend/dist` | 빌드된 프론트 경로 |
```

`## 쓰는 법` 앞에 절을 하나 더한다.

```markdown
## 들어오기

사이트를 열면 먼저 **입장 비밀번호**를 묻습니다. 동아리원끼리 나눠 갖는 하나의
비밀번호이고, 이걸 넣어야 시간표가 보입니다. 주소만 아는 사람은 데이터를 받아갈
수 없습니다 — 화면뿐 아니라 서버 요청 자체가 막힙니다.

한 번 넣으면 그 브라우저에 남아 다음부터는 묻지 않습니다. 관리자가 비밀번호를
바꾸면 모두 다시 넣어야 합니다.

비밀번호가 셋이라 헷갈리기 쉬우니 정리하면 이렇습니다.

| 비밀번호 | 무엇을 여는가 | 누가 아는가 |
|---|---|---|
| 입장 | 사이트 자체 | 동아리원 전체가 같은 것 |
| 개인 4자리 | 내 일정 고치기 | 본인만 |
| 관리자 | 전부 고치기 · 입장 설정 | 운영하는 사람 |
```

`## 배포` 절을 아래로 바꾼다.

```markdown
## 배포

디스크를 붙일 수 있는 곳이면 어디든 됩니다. SQLite 파일이 볼륨에 있어야 다시
배포해도 데이터가 남습니다.

### Railway

1. 이 저장소를 GitHub 에 올립니다
2. Railway 에서 **New Project → Deploy from GitHub repo** 로 저장소를 고릅니다
   (`Dockerfile` 을 알아서 찾습니다)
3. **Variables** 에 둘을 넣습니다

   ```
   ADMIN_PASSWORD = 충분히 긴 비밀번호
   GATE_PASSWORD  = 동아리원에게 나눠 줄 비밀번호
   ```

4. **Settings → Volumes** 에서 볼륨을 만들고 마운트 경로를 `/data` 로 합니다.
   **이걸 빠뜨리면 다시 배포할 때마다 등록한 이름과 일정이 사라집니다.**
5. **Settings → Networking** 에서 도메인을 만들면 주소가 나옵니다

### 직접 돌리기

```bash
docker build -t club-schedule .
docker run -d -p 8000:8000 \
  -e ADMIN_PASSWORD='충분히 긴 비밀번호' \
  -e GATE_PASSWORD='동아리 입장 비밀번호' \
  -v club-data:/data --restart unless-stopped club-schedule
```

uvicorn 워커는 **1개**여야 합니다. 비밀번호 시도 제한과 입장 검증 기억이 프로세스
메모리에 있어서, 워커가 여러 개면 제한이 워커 수만큼 느슨해집니다.

> **Vercel 은 쓸 수 없습니다.** Python 함수가 서버리스로 돌아 파일시스템이 읽기
> 전용이고 요청마다 인스턴스가 새로 뜹니다. SQLite 에 쓴 데이터가 남지 않습니다.
```

- [ ] **Step 4: 전체 검증**

```bash
cd backend  && .venv/Scripts/python -m pytest -q
cd frontend && npm test && npm run build
```

기대 출력: 백엔드 `176 passed`, 프론트 `91 passed`, 빌드 성공

- [ ] **Step 5: 도커 이미지가 실제로 뜨는지 확인**

```bash
docker build -t club-schedule .
docker run --rm -p 8000:8000 -e ADMIN_PASSWORD=test-admin -e GATE_PASSWORD=test-gate club-schedule
```

`http://localhost:8000` 에서 첫 화면이 뜨고 `test-gate` 로 들어가지는지 확인한다.
환경변수를 하나 빼고 실행하면 서버가 시작을 거부하는지도 확인한다.

- [ ] **Step 6: 커밋**

```bash
git add README.md Dockerfile
git commit -m "docs: describe the entry gate and deployment"
```

---

## 완료 조건

- 입장 비밀번호 없이 `GET /api/board` 를 부르면 `401` 과 `X-Gate: required`
- 첫 화면에서 비밀번호를 넣으면 시간표가 열리고, 새로고침해도 다시 묻지 않는다
- 관리자가 제목·설명을 고치면 첫 화면에 그대로 반영된다
- 관리자가 입장 비밀번호를 바꾸면 **다른 사람은 다시 입력**해야 하고 **바꾼 본인은 튕기지 않는다**
- `GATE_PASSWORD` 없이 띄우면 서버가 시작을 거부한다
- 서버를 다시 띄워도 관리자가 사이트에서 바꾼 입장 비밀번호가 유지된다
- 백엔드 176개, 프론트 91개 테스트 통과
