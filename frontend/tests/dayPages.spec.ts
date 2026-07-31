import { describe, expect, it } from 'vitest'
import { DAY_NAMES } from '@/constants'
import { daysPerPage, pageLabel, splitIntoPages } from '@/utils/dayPages'

describe('daysPerPage', () => {
  it('넉넉하면 일주일이 한 페이지다', () => {
    expect(daysPerPage(3000, 2, 96)).toBe(7)
  })

  it('세 명이 들어갈 폭이면 세 요일까지', () => {
    // 요일 하나 = 3명 x 96px = 288px. 1000px 이면 세 개.
    expect(daysPerPage(1000, 3, 96)).toBe(3)
  })

  it('한 요일도 벅차면 그래도 하나는 보여 준다', () => {
    expect(daysPerPage(200, 10, 96)).toBe(1)
  })

  it('선택된 사람이 없으면 일주일을 통째로 본다', () => {
    expect(daysPerPage(1000, 0, 96)).toBe(7)
  })
})

describe('splitIntoPages', () => {
  it('일곱이 다 들어가면 한 페이지다', () => {
    expect(splitIntoPages(7)).toEqual([[0, 1, 2, 3, 4, 5, 6]])
  })

  it('셋씩이면 3·2·2 로 고르게 나눈다', () => {
    expect(splitIntoPages(3).map((page) => page.length)).toEqual([3, 2, 2])
  })

  it('넷씩이면 4·3 이다', () => {
    expect(splitIntoPages(4)).toEqual([
      [0, 1, 2, 3],
      [4, 5, 6],
    ])
  })

  it('하나씩이면 이레가 각각 한 페이지다', () => {
    expect(splitIntoPages(1)).toHaveLength(7)
  })

  it('모든 요일이 빠짐없이 한 번씩 들어간다', () => {
    for (const perPage of [1, 2, 3, 4, 5, 6, 7]) {
      const flat = splitIntoPages(perPage).flat()
      expect(flat).toEqual(DAY_NAMES.map((_, index) => index))
    }
  })
})

describe('pageLabel', () => {
  it('여러 날이면 범위로 적는다', () => {
    expect(pageLabel([0, 1, 2])).toBe('월–수')
  })

  it('하루면 그 이름만', () => {
    expect(pageLabel([6])).toBe('일')
  })

  it('빈 페이지는 빈 문자열', () => {
    expect(pageLabel([])).toBe('')
  })
})
