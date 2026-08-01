import { describe, expect, it } from 'vitest'
import { DAY_NAMES, PALETTE } from '@/constants'
import type { Schedule } from '@/types'
import { blockColor, nextColorMode } from '@/utils/blockColor'

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return {
    id: 1,
    member_id: 1,
    day_of_week: 0,
    start_slot: 6,
    end_slot: 10,
    title: '수업',
    color: '#f4a69c',
    ...overrides,
  }
}

const ORDER = new Map([
  [1, 0],
  [2, 1],
  [3, 2],
])

describe('nextColorMode', () => {
  it('셋을 돌아 제자리로 온다', () => {
    expect(nextColorMode('own')).toBe('day')
    expect(nextColorMode('day')).toBe('member')
    expect(nextColorMode('member')).toBe('own')
  })
})

describe('blockColor', () => {
  it('기본은 만든 사람이 고른 색 그대로', () => {
    expect(blockColor(schedule({ color: '#98d6d2' }), 'own', ORDER)).toBe(
      '#98d6d2',
    )
  })

  it('요일별이면 같은 요일이 같은 색이다', () => {
    const monday = blockColor(schedule({ day_of_week: 0, member_id: 1 }), 'day', ORDER)
    const alsoMonday = blockColor(
      schedule({ day_of_week: 0, member_id: 3, color: '#cec7bc' }),
      'day',
      ORDER,
    )
    expect(alsoMonday).toBe(monday)
  })

  it('요일별이면 다른 요일은 다른 색이다', () => {
    const seen = DAY_NAMES.map((_, day) =>
      blockColor(schedule({ day_of_week: day }), 'day', ORDER),
    )
    expect(new Set(seen).size).toBe(DAY_NAMES.length)
  })

  it('인원별이면 같은 사람이 어느 요일에 있든 같은 색이다', () => {
    const monday = blockColor(schedule({ member_id: 2, day_of_week: 0 }), 'member', ORDER)
    const friday = blockColor(schedule({ member_id: 2, day_of_week: 4 }), 'member', ORDER)
    expect(friday).toBe(monday)
  })

  it('인원별이면 다른 사람은 다른 색이다', () => {
    const first = blockColor(schedule({ member_id: 1 }), 'member', ORDER)
    const second = blockColor(schedule({ member_id: 2 }), 'member', ORDER)
    expect(second).not.toBe(first)
  })

  it('인원이 팔레트보다 많으면 색이 돌아온다', () => {
    const many = new Map([[99, PALETTE.length]])
    expect(blockColor(schedule({ member_id: 99 }), 'member', many)).toBe(PALETTE[0])
  })

  it('화면에 없는 사람도 색을 받는다', () => {
    expect(blockColor(schedule({ member_id: 404 }), 'member', ORDER)).toBe(PALETTE[0])
  })
})
