export interface Category {
  id: number
  name: string
  sort_order: number
}

export interface Member {
  id: number
  name: string
  category_id: number
  sort_order: number
}

export interface Schedule {
  id: number
  member_id: number
  day_of_week: number
  start_slot: number
  end_slot: number
  title: string
  color: string
}

export interface Board {
  categories: Category[]
  members: Member[]
  schedules: Schedule[]
}

/** 요청에 실어 보낼 인증 정보. 둘 다 비어 있으면 익명이다. */
export interface Credentials {
  adminPassword?: string
  memberId?: number
  memberPassword?: string
}
