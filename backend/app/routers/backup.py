"""DB 통째로 내려받기. 서버를 옮기거나 백업해 둘 때 쓴다."""

import os
import sqlite3
import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.auth import Actor, require_admin, resolve_actor
from app.routers.board import get_conn

router = APIRouter(prefix="/api/backup")


@router.get("")
def download_backup(
    actor: Actor = Depends(resolve_actor),
    conn: sqlite3.Connection = Depends(get_conn),
) -> FileResponse:
    """관리자만. 서버가 돌아가는 중에도 안전한 복사본을 뜬다.

    파일을 그냥 복사하면 누군가 일정을 저장하는 순간에 걸려 깨진 DB 를 받을
    수 있다. SQLite 의 온라인 백업은 그 시점의 앞뒤가 맞는 상태를 보장한다.

    받은 파일에는 비밀번호 해시까지 들어 있다. 그래서 관리자만 받을 수
    있고, 그대로 옮기면 동아리원이 비밀번호를 다시 만들지 않아도 된다.
    """
    require_admin(actor)

    handle, path = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    target = sqlite3.connect(path)
    try:
        conn.backup(target)
    finally:
        target.close()

    # 시각은 서버 시간대다. 배포처가 UTC 면 파일 이름도 UTC 로 찍힌다.
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return FileResponse(
        path,
        media_type="application/vnd.sqlite3",
        filename=f"schedule-{stamp}.db",
        # 보내고 나서 임시 파일을 지운다.
        background=BackgroundTask(os.unlink, path),
    )
