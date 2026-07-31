"""API 입출력 모델. 출력 모델에는 password_hash가 절대 들어가지 않는다."""

from pydantic import BaseModel, Field

from app.constants import MEMBER_PASSWORD_PATTERN, NAME_MAX_LEN


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

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LEN)


class OrderIn(BaseModel):
    ordered_ids: list[int]

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
