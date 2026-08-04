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
