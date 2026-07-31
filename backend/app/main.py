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


def create_production_app() -> FastAPI:
    """운영용 앱. uvicorn은 --factory 로 이 함수를 부른다.

    모듈을 임포트하는 것만으로 DB를 열거나 ADMIN_PASSWORD를 요구하면
    테스트가 환경변수에 묶인다. 그래서 앱 생성은 호출 시점으로 미룬다.
    """
    settings = load_settings()
    conn = connect(settings.db_path)
    initialize(conn, hash_password(settings.admin_password))
    return create_app(conn, AttemptLimiter())
