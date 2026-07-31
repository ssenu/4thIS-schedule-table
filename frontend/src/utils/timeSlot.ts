import { DAY_NAMES, DAY_START_HOUR, SLOT_COUNT, SLOT_MINUTES } from '@/constants'

export interface SlotOption {
  value: number
  label: string
}

/** 슬롯 번호를 "HH:MM"으로. SLOT_COUNT는 "24:00"이다. */
export function slotToTime(slot: number): string {
  if (slot < 0 || slot > SLOT_COUNT) {
    throw new RangeError(`슬롯 범위를 벗어났습니다: ${slot}`)
  }
  const minutes = DAY_START_HOUR * 60 + slot * SLOT_MINUTES
  const hh = String(Math.floor(minutes / 60)).padStart(2, '0')
  const mm = String(minutes % 60).padStart(2, '0')
  return `${hh}:${mm}`
}

/** "HH:MM"을 슬롯 번호로. 격자에 없는 시각은 거부한다. */
export function timeToSlot(text: string): number {
  const [hourText, minuteText] = text.split(':')
  const minutes = Number(hourText) * 60 + Number(minuteText)
  const offset = minutes - DAY_START_HOUR * 60
  if (offset < 0 || offset % SLOT_MINUTES !== 0) {
    throw new RangeError(`격자에 없는 시각입니다: ${text}`)
  }
  const slot = offset / SLOT_MINUTES
  if (slot > SLOT_COUNT) {
    throw new RangeError(`격자에 없는 시각입니다: ${text}`)
  }
  return slot
}

/** "월 09:00~13:00" — 목록과 툴팁에 쓰는 한 줄 설명. */
export function describeSchedule(day: number, start: number, end: number): string {
  return `${DAY_NAMES[day]} ${slotToTime(start)}~${slotToTime(end)}`
}

/** 시작·종료 드롭다운에 쓸 전체 선택지. */
export function slotOptions(): SlotOption[] {
  return Array.from({ length: SLOT_COUNT + 1 }, (_, slot) => ({
    value: slot,
    label: slotToTime(slot),
  }))
}
