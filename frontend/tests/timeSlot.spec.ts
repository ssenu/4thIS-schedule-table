import { describe, expect, it } from 'vitest'
import { SLOT_COUNT } from '@/constants'
import {
  describeSchedule,
  slotOptions,
  slotToTime,
  timeToSlot,
} from '@/utils/timeSlot'

describe('slotToTime', () => {
  it('첫 슬롯은 하루 시작 시각이다', () => {
    expect(slotToTime(0)).toBe('06:00')
  })

  it('슬롯 6은 09:00이다', () => {
    expect(slotToTime(6)).toBe('09:00')
  })

  it('마지막 경계는 24:00이다', () => {
    expect(slotToTime(SLOT_COUNT)).toBe('24:00')
  })

  it('30분 단위를 표현한다', () => {
    expect(slotToTime(1)).toBe('06:30')
    expect(slotToTime(35)).toBe('23:30')
  })
})

describe('timeToSlot', () => {
  it('모든 슬롯을 왕복 변환한다', () => {
    for (let slot = 0; slot <= SLOT_COUNT; slot += 1) {
      expect(timeToSlot(slotToTime(slot))).toBe(slot)
    }
  })

  it('격자에 없는 시각을 거부한다', () => {
    expect(() => timeToSlot('09:15')).toThrow()
    expect(() => timeToSlot('05:30')).toThrow()
  })
})

describe('describeSchedule', () => {
  it('한 줄 문장으로 만든다', () => {
    expect(describeSchedule(0, 6, 14)).toBe('월 09:00~13:00')
    expect(describeSchedule(6, 0, 1)).toBe('일 06:00~06:30')
  })
})

describe('slotOptions', () => {
  it('0부터 마지막 경계까지 모두 준다', () => {
    const options = slotOptions()
    expect(options).toHaveLength(SLOT_COUNT + 1)
    expect(options[0]).toEqual({ value: 0, label: '06:00' })
    expect(options[SLOT_COUNT]).toEqual({ value: SLOT_COUNT, label: '24:00' })
  })
})
