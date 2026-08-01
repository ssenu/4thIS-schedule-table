import { PALETTE } from '@/constants'
import type { Schedule } from '@/types'

/**
 * 블록 색을 무엇으로 정할지.
 *
 * - own: 일정을 만든 사람이 고른 색
 * - day: 같은 요일끼리 한 색 — 요일 덩어리가 눈에 들어온다
 * - member: 같은 사람끼리 한 색 — 한 사람의 하루가 눈에 들어온다
 */
export type ColorMode = 'own' | 'day' | 'member'

export const COLOR_MODES: ColorMode[] = ['own', 'day', 'member']

export const COLOR_MODE_LABEL: Record<ColorMode, string> = {
  own: '기본',
  day: '요일별',
  member: '인원별',
}

/** 지금 모드 다음 차례. 버튼 하나로 셋을 돌린다. */
export function nextColorMode(mode: ColorMode): ColorMode {
  const at = COLOR_MODES.indexOf(mode)
  return COLOR_MODES[(at + 1) % COLOR_MODES.length]
}

/**
 * 블록에 칠할 색.
 *
 * memberIndex 는 화면에 놓인 순서다. 그 자리로 팔레트를 골라야 같은 사람이
 * 어느 요일에 있든 같은 색을 갖는다. 인원이 팔레트보다 많으면 색이 돌아온다.
 */
export function blockColor(
  schedule: Pick<Schedule, 'day_of_week' | 'member_id' | 'color'>,
  mode: ColorMode,
  memberIndex: ReadonlyMap<number, number>,
): string {
  if (mode === 'day') {
    return PALETTE[schedule.day_of_week % PALETTE.length]
  }
  if (mode === 'member') {
    const at = memberIndex.get(schedule.member_id) ?? 0
    return PALETTE[at % PALETTE.length]
  }
  return schedule.color
}
