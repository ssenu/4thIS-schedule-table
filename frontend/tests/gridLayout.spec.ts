import { describe, expect, it } from 'vitest'
import { DAY_NAMES, SLOT_COUNT } from '@/constants'
import {
  HEADER_ROWS,
  buildBlocks,
  buildColumns,
  buildDayHeaders,
  rowForSlot,
  totalColumns,
} from '@/utils/gridLayout'
import type { Member, Schedule } from '@/types'

function member(id: number, name: string, sortOrder = id): Member {
  return { id, name, category_id: 1, sort_order: sortOrder }
}

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return {
    id: 1,
    member_id: 1,
    day_of_week: 0,
    start_slot: 6,
    end_slot: 14,
    title: '전공수업',
    color: '#ef4444',
    ...overrides,
  }
}

const THREE = [member(1, '철수'), member(2, '영희'), member(3, '민수')]

describe('buildColumns', () => {
  it('요일마다 선택 인원만큼 열을 만든다', () => {
    expect(buildColumns(THREE)).toHaveLength(DAY_NAMES.length * 3)
  })

  it('첫 열은 시간축 바로 오른쪽이다', () => {
    expect(buildColumns(THREE)[0].gridColumn).toBe(2)
  })

  it('열은 요일 먼저, 그 안에서 멤버 순서로 늘어선다', () => {
    const columns = buildColumns(THREE)
    expect(columns[0]).toMatchObject({ day: 0, gridColumn: 2 })
    expect(columns[2]).toMatchObject({ day: 0, gridColumn: 4 })
    expect(columns[3]).toMatchObject({ day: 1, gridColumn: 5 })
  })

  it('멤버가 없으면 열도 없다', () => {
    expect(buildColumns([])).toEqual([])
  })
})

describe('buildDayHeaders', () => {
  it('요일마다 인원수만큼 칸을 병합한다', () => {
    const headers = buildDayHeaders(3)
    expect(headers).toHaveLength(7)
    expect(headers[0]).toEqual({
      day: 0,
      label: '월',
      gridColumnStart: 2,
      span: 3,
    })
    expect(headers[1].gridColumnStart).toBe(5)
  })

  it('멤버가 없으면 헤더도 없다', () => {
    expect(buildDayHeaders(0)).toEqual([])
  })
})

describe('rowForSlot', () => {
  it('첫 슬롯은 헤더 두 줄 다음이다', () => {
    expect(rowForSlot(0)).toBe(HEADER_ROWS + 1)
  })

  it('마지막 경계는 격자 끝이다', () => {
    expect(rowForSlot(SLOT_COUNT)).toBe(HEADER_ROWS + 1 + SLOT_COUNT)
  })
})

describe('totalColumns', () => {
  it('시간축 한 열을 더한다', () => {
    expect(totalColumns(3)).toBe(1 + 21)
    expect(totalColumns(0)).toBe(1)
  })
})

describe('buildBlocks', () => {
  it('일정 하나를 블록 하나로 만든다', () => {
    const blocks = buildBlocks(THREE, [schedule()])
    expect(blocks).toHaveLength(1)
  })

  it('4시간 일정은 8칸을 차지하는 블록 하나가 된다', () => {
    const [block] = buildBlocks(THREE, [schedule({ start_slot: 6, end_slot: 14 })])
    expect(block.gridRowEnd - block.gridRowStart).toBe(8)
    expect(block.gridRowStart).toBe(rowForSlot(6))
    expect(block.gridRowEnd).toBe(rowForSlot(14))
  })

  it('30분 일정도 블록 하나다', () => {
    const [block] = buildBlocks(THREE, [schedule({ start_slot: 0, end_slot: 1 })])
    expect(block.gridRowEnd - block.gridRowStart).toBe(1)
  })

  it('멤버와 요일에 맞는 열에 놓인다', () => {
    const [block] = buildBlocks(THREE, [schedule({ member_id: 2, day_of_week: 1 })])
    expect(block.gridColumn).toBe(2 + 1 * 3 + 1)
  })

  it('선택되지 않은 멤버의 일정은 빠진다', () => {
    const blocks = buildBlocks([member(1, '철수')], [schedule({ member_id: 2 })])
    expect(blocks).toEqual([])
  })

  it('여러 일정을 모두 배치한다', () => {
    const blocks = buildBlocks(THREE, [
      schedule({ id: 1, member_id: 1, day_of_week: 0 }),
      schedule({ id: 2, member_id: 3, day_of_week: 4 }),
    ])
    expect(blocks.map((b) => b.schedule.id)).toEqual([1, 2])
  })
})

describe('요일 페이지', () => {
  it('페이지에 실린 요일만큼만 열을 만든다', () => {
    expect(buildColumns(THREE, [3, 4, 5, 6])).toHaveLength(4 * 3)
  })

  it('페이지 안에서는 왼쪽 끝부터 자리를 잡는다', () => {
    const [first] = buildColumns(THREE, [3, 4, 5, 6])
    expect(first).toMatchObject({ day: 3, gridColumn: 2 })
  })

  it('헤더도 그 페이지의 요일만 이름을 단다', () => {
    const headers = buildDayHeaders(3, [3, 4, 5, 6])
    expect(headers.map((head) => head.label)).toEqual(['목', '금', '토', '일'])
    expect(headers[0].gridColumnStart).toBe(2)
  })

  it('다른 페이지의 일정은 자리가 없어 빠진다', () => {
    const monday = schedule({ day_of_week: 0 })
    expect(buildBlocks(THREE, [monday], [3, 4, 5, 6])).toEqual([])
    expect(buildBlocks(THREE, [monday], [0, 1, 2])).toHaveLength(1)
  })

  it('열 개수도 페이지 기준으로 센다', () => {
    expect(totalColumns(3, 4)).toBe(1 + 12)
  })
})
