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
