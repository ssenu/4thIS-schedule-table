import { describe, expect, it } from 'vitest'
import { SLOT_COUNT } from '@/constants'
import {
  clashes,
  fromDrag,
  moveTo,
  resizeEnd,
  resizeStart,
} from '@/utils/draftBox'

/** 09:00~11:00 (슬롯 6부터 4칸). 대부분의 시험에서 출발점으로 쓴다. */
const BOX = { day: 0, start: 6, end: 10 }

describe('fromDrag', () => {
  it('아래로 끌면 누른 칸부터 끝난 칸까지', () => {
    expect(fromDrag(2, 6, 9)).toEqual({ day: 2, start: 6, end: 10 })
  })

  it('위로 끌어도 같은 구간이 된다', () => {
    expect(fromDrag(2, 9, 6)).toEqual({ day: 2, start: 6, end: 10 })
  })

  it('한 칸만 누르면 30분짜리가 된다', () => {
    expect(fromDrag(2, 6, 6)).toEqual({ day: 2, start: 6, end: 7 })
  })

  it('격자 밖으로는 나가지 않는다', () => {
    expect(fromDrag(2, 0, -5)).toEqual({ day: 2, start: 0, end: 1 })
    expect(fromDrag(2, SLOT_COUNT - 1, 99)).toEqual({
      day: 2,
      start: SLOT_COUNT - 1,
      end: SLOT_COUNT,
    })
  })
})

describe('resizeStart', () => {
  it('위 끝을 올리면 시작만 바뀐다', () => {
    expect(resizeStart(BOX, 3)).toEqual({ day: 0, start: 3, end: 10 })
  })

  it('아래로 밀어도 30분은 남긴다', () => {
    expect(resizeStart(BOX, 20)).toEqual({ day: 0, start: 9, end: 10 })
  })

  it('격자 위로는 나가지 않는다', () => {
    expect(resizeStart(BOX, -4)).toEqual({ day: 0, start: 0, end: 10 })
  })
})

describe('resizeEnd', () => {
  it('아래 끝을 내리면 끝만 바뀐다. 누른 칸은 포함된다', () => {
    expect(resizeEnd(BOX, 12)).toEqual({ day: 0, start: 6, end: 13 })
  })

  it('위로 밀어도 30분은 남긴다', () => {
    expect(resizeEnd(BOX, 2)).toEqual({ day: 0, start: 6, end: 7 })
  })

  it('격자 아래로는 나가지 않는다', () => {
    expect(resizeEnd(BOX, 99)).toEqual({ day: 0, start: 6, end: SLOT_COUNT })
  })
})

describe('moveTo', () => {
  it('요일과 자리를 옮겨도 길이는 그대로다', () => {
    expect(moveTo(BOX, 4, 20)).toEqual({ day: 4, start: 20, end: 24 })
  })

  it('아래 경계에 닿으면 거기서 멈춘다', () => {
    expect(moveTo(BOX, 4, SLOT_COUNT - 2)).toEqual({
      day: 4,
      start: SLOT_COUNT - 4,
      end: SLOT_COUNT,
    })
  })

  it('위 경계에 닿아도 마찬가지다', () => {
    expect(moveTo(BOX, 4, -10)).toEqual({ day: 4, start: 0, end: 4 })
  })

  it('요일만 바꾸고 자리는 그대로 둘 수 있다', () => {
    expect(moveTo(BOX, 6, BOX.start)).toEqual({ day: 6, start: 6, end: 10 })
  })
})

describe('clashes', () => {
  const 화요일_9시부터11시 = {
    id: 1,
    member_id: 7,
    day_of_week: 1,
    start_slot: 6,
    end_slot: 10,
    title: '전공수업',
    color: '#a9dcb5',
  }

  it('같은 요일에서 시간이 겹치면 부딪힌다', () => {
    const box = { day: 1, start: 8, end: 12 }
    expect(clashes(box, [화요일_9시부터11시], 7)).toBe(true)
  })

  it('끝나는 칸과 시작하는 칸이 맞닿는 것은 겹침이 아니다', () => {
    expect(clashes({ day: 1, start: 10, end: 14 }, [화요일_9시부터11시], 7)).toBe(
      false,
    )
    expect(clashes({ day: 1, start: 2, end: 6 }, [화요일_9시부터11시], 7)).toBe(
      false,
    )
  })

  it('요일이 다르면 상관없다', () => {
    expect(clashes({ day: 2, start: 8, end: 12 }, [화요일_9시부터11시], 7)).toBe(
      false,
    )
  })

  it('다른 사람 일정과는 부딪히지 않는다', () => {
    expect(clashes({ day: 1, start: 8, end: 12 }, [화요일_9시부터11시], 99)).toBe(
      false,
    )
  })

  it('옮기는 중인 자기 자신은 빼고 본다', () => {
    const box = { day: 1, start: 7, end: 11 }
    expect(clashes(box, [화요일_9시부터11시], 7)).toBe(true)
    expect(clashes(box, [화요일_9시부터11시], 7, 1)).toBe(false)
  })

  it('완전히 품는 경우도 겹침이다', () => {
    expect(clashes({ day: 1, start: 4, end: 14 }, [화요일_9시부터11시], 7)).toBe(
      true,
    )
    expect(clashes({ day: 1, start: 7, end: 9 }, [화요일_9시부터11시], 7)).toBe(
      true,
    )
  })
})
