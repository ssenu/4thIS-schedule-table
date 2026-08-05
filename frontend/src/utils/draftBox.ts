import { SLOT_COUNT } from '@/constants'
import type { Schedule } from '@/types'

/**
 * 격자에 놓인 초안 한 칸.
 *
 * end 는 배타적이다. 09:00~11:00 짜리는 {start: 6, end: 10} 으로, 일정
 * 자체와 같은 규칙을 쓴다 — 그대로 서버로 보낼 수 있다.
 */
export interface DraftBox {
  day: number
  /** 0..SLOT_COUNT-1, 포함 */
  start: number
  /** 1..SLOT_COUNT, 배타 */
  end: number
}

/** 30분. 이보다 짧으면 무엇을 그린 것인지 알아볼 수 없다. */
const MIN_LENGTH = 1

/** 칸 번호를 격자 안으로 들인다. 마지막 칸은 SLOT_COUNT-1 이다. */
function clampSlot(slot: number): number {
  return Math.max(0, Math.min(SLOT_COUNT - 1, Math.round(slot)))
}

/**
 * 처음 그릴 때. 누른 칸과 손을 뗀 칸 사이를 덮는다.
 *
 * 위로 끌든 아래로 끌든 같은 구간이 된다. 한 칸만 눌렀으면 30분짜리다.
 */
export function fromDrag(
  day: number,
  anchor: number,
  cursor: number,
): DraftBox {
  const a = clampSlot(anchor)
  const b = clampSlot(cursor)
  return { day, start: Math.min(a, b), end: Math.max(a, b) + 1 }
}

/** 위 끝을 옮긴다. 아래 끝은 그대로 두고, 30분은 남긴다. */
export function resizeStart(box: DraftBox, slot: number): DraftBox {
  return { ...box, start: Math.min(clampSlot(slot), box.end - MIN_LENGTH) }
}

/** 아래 끝을 옮긴다. 손이 놓인 칸은 구간에 포함된다. */
export function resizeEnd(box: DraftBox, slot: number): DraftBox {
  return { ...box, end: Math.max(clampSlot(slot) + 1, box.start + MIN_LENGTH) }
}

/**
 * 통째로 옮긴다. 길이는 변하지 않는다.
 *
 * 격자 끝에 닿으면 거기서 멈춘다 — 길이를 줄여 가며 밀고 나가지 않는다.
 */
export function moveTo(box: DraftBox, day: number, topSlot: number): DraftBox {
  const length = box.end - box.start
  const start = Math.max(0, Math.min(Math.round(topSlot), SLOT_COUNT - length))
  return { day, start, end: start + length }
}

/**
 * 이미 있는 일정과 자리가 겹치는지.
 *
 * 서버도 저장할 때 같은 판정을 한다. 여기서 먼저 보는 것은 저장을 눌러
 * 거절당하기 전에 빨갛게 알려 주기 위해서다.
 *
 * 끝나는 칸과 시작하는 칸이 맞닿는 것은 겹침이 아니다 — 11:00 에 끝나는
 * 수업과 11:00 에 시작하는 알바는 나란히 있을 수 있다.
 *
 * @param ignoreId 옮기는 중인 일정 자신. 제 자리와 부딪혔다고 하면 안 된다.
 */
export function clashes(
  box: DraftBox,
  schedules: Schedule[],
  memberId: number,
  ignoreId?: number,
): boolean {
  return schedules.some(
    (s) =>
      s.member_id === memberId &&
      s.day_of_week === box.day &&
      s.id !== ignoreId &&
      box.start < s.end_slot &&
      s.start_slot < box.end,
  )
}
