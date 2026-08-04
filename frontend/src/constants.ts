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

/**
 * 격자 치수. style.css 의 --ruler-w, --col-min 과 같은 값이어야 한다.
 * 한 페이지에 요일 몇 개가 들어가는지 재는 계산이 이 값을 쓴다.
 */
export const RULER_WIDTH = 46
export const MIN_COLUMN_WIDTH = 96

// backend/app/gate.py 의 DEFAULT_TITLE · DEFAULT_INTRO 와 같아야 한다.
export const DEFAULT_GATE_TITLE = '동아리 주간 시간표'
export const DEFAULT_GATE_INTRO =
  '동아리원만 볼 수 있습니다. 받은 비밀번호를 넣어 주세요.'
