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
