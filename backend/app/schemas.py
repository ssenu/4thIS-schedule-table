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
