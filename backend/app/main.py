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
from app.routers import backup
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
    app.include_router(backup.router)

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
