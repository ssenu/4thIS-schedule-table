"""스펙에 고정된 값. 다른 모듈은 숫자를 직접 쓰지 않고 여기서 가져온다."""

DAY_START_HOUR = 6
SLOT_MINUTES = 30
SLOT_COUNT = 36  # 06:00 ~ 24:00

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

# 파스텔 열 가지. 명도가 고르게 높아 글자는 항상 잉크색으로 얹힌다.
PALETTE = [
    "#f4a69c",  # 코랄
    "#f7c99b",  # 살구
    "#efdd9a",  # 버터
    "#a9dcb5",  # 민트
    "#98d6d2",  # 아쿠아
    "#a7c4f0",  # 하늘
    "#b6b4ec",  # 라벤더
    "#cfafea",  # 라일락
    "#f2aecb",  # 로즈
    "#cec7bc",  # 모래
]

# 진한 팔레트로 저장된 기존 일정을 같은 자리의 파스텔로 옮긴다.
# 이 표가 없으면 예전 일정은 색이 팔레트 밖이라 수정할 수 없게 된다.
LEGACY_COLORS = {
    "#ef4444": "#f4a69c",
    "#f97316": "#f7c99b",
    "#eab308": "#efdd9a",
    "#22c55e": "#a9dcb5",
    "#14b8a6": "#98d6d2",
    "#3b82f6": "#a7c4f0",
    "#6366f1": "#b6b4ec",
    "#a855f7": "#cfafea",
    "#ec4899": "#f2aecb",
    "#78716c": "#cec7bc",
}

NAME_MAX_LEN = 20
TITLE_MAX_LEN = 30
MEMBER_PASSWORD_PATTERN = r"^\d{4}$"

MAX_FAILED_ATTEMPTS = 10
LOCKOUT_SECONDS = 600

DEFAULT_CATEGORIES = ["1학년", "2학년", "3학년"]

