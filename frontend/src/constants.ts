// backend/app/constants.py 와 값이 일치해야 한다.
export const DAY_START_HOUR = 6
export const SLOT_MINUTES = 30
export const SLOT_COUNT = 36 // 06:00 ~ 24:00

export const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'] as const

// 파스텔 열 가지. 명도가 고르게 높아 글자는 항상 잉크색으로 얹힌다.
export const PALETTE = [
  '#f4a69c', // 코랄
  '#f7c99b', // 살구
  '#efdd9a', // 버터
  '#a9dcb5', // 민트
  '#98d6d2', // 아쿠아
  '#a7c4f0', // 하늘
  '#b6b4ec', // 라벤더
  '#cfafea', // 라일락
  '#f2aecb', // 로즈
  '#cec7bc', // 모래
] as const

export const NAME_MAX_LEN = 20
export const TITLE_MAX_LEN = 30

