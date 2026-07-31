import { DAY_NAMES } from '@/constants'
import type { Member, Schedule } from '@/types'

/** 요일 줄과 이름 줄, 두 줄이 격자 위에 얹힌다. */
export const HEADER_ROWS = 2
/** 맨 왼쪽 시간축이 차지하는 열 번호. */
export const TIME_COLUMN = 1
/** 페이지를 나누지 않을 때의 기본값 — 월요일부터 일요일까지. */
export const EVERY_DAY = DAY_NAMES.map((_, index) => index)

export interface GridColumn {
  day: number
  member: Member
  gridColumn: number
}

export interface DayHeader {
  day: number
  label: string
  gridColumnStart: number
  span: number
}

export interface ScheduleBlock {
  schedule: Schedule
  gridColumn: number
  gridRowStart: number
  gridRowEnd: number
}

/** 슬롯 번호를 CSS grid-row 선 번호로. */
export function rowForSlot(slot: number): number {
  return HEADER_ROWS + 1 + slot
}

/** 시간축까지 포함한 전체 열 개수. */
export function totalColumns(
  memberCount: number,
  dayCount: number = DAY_NAMES.length,
): number {
  return TIME_COLUMN + dayCount * memberCount
}

/**
 * 요일 바깥, 멤버 안쪽 순서로 열을 펼친다.
 *
 * days 는 이 페이지가 보여 줄 요일이다. 열 번호는 요일의 실제 번호가 아니라
 * 페이지 안에서의 자리로 매겨지므로, 목·금·토·일 페이지도 왼쪽 끝부터 채워진다.
 */
export function buildColumns(
  members: Member[],
  days: number[] = EVERY_DAY,
): GridColumn[] {
  const columns: GridColumn[] = []
  days.forEach((day, dayIndex) => {
    members.forEach((member, index) => {
      columns.push({
        day,
        member,
        gridColumn: TIME_COLUMN + 1 + dayIndex * members.length + index,
      })
    })
  })
  return columns
}

/** 요일 헤더는 그 요일의 멤버 열 전체를 덮는다. */
export function buildDayHeaders(
  memberCount: number,
  days: number[] = EVERY_DAY,
): DayHeader[] {
  if (memberCount === 0) {
    return []
  }
  return days.map((day, dayIndex) => ({
    day,
    label: DAY_NAMES[day],
    gridColumnStart: TIME_COLUMN + 1 + dayIndex * memberCount,
    span: memberCount,
  }))
}

/**
 * 일정 하나를 블록 하나로 바꾼다.
 *
 * 몇 슬롯에 걸치든 블록은 하나다. 09:00~13:00 일정은 8칸 높이의
 * 세로로 긴 블록 하나가 되고, 제목은 그 안에 한 번만 쓰인다.
 * 이 페이지에 없는 요일이나 고르지 않은 사람의 일정은 자리가 없어 빠진다.
 */
export function buildBlocks(
  members: Member[],
  schedules: Schedule[],
  days: number[] = EVERY_DAY,
): ScheduleBlock[] {
  const columnOf = new Map<string, number>()
  for (const column of buildColumns(members, days)) {
    columnOf.set(`${column.day}:${column.member.id}`, column.gridColumn)
  }

  const blocks: ScheduleBlock[] = []
  for (const schedule of schedules) {
    const gridColumn = columnOf.get(
      `${schedule.day_of_week}:${schedule.member_id}`,
    )
    if (gridColumn === undefined) {
      continue
    }
    blocks.push({
      schedule,
      gridColumn,
      gridRowStart: rowForSlot(schedule.start_slot),
      gridRowEnd: rowForSlot(schedule.end_slot),
    })
  }
  return blocks
}
