import { SLOT_COUNT } from '@/constants'

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
