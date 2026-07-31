// backend/app/constants.py 와 값이 일치해야 한다.
export const DAY_START_HOUR = 6
export const SLOT_MINUTES = 30
export const SLOT_COUNT = 36 // 06:00 ~ 24:00

export const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'] as const

export const PALETTE = [
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#14b8a6',
  '#3b82f6',
  '#6366f1',
  '#a855f7',
  '#ec4899',
  '#78716c',
] as const

export const NAME_MAX_LEN = 20
export const TITLE_MAX_LEN = 30
