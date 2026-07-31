import { describe, expect, it } from 'vitest'
import { PALETTE } from '@/constants'
import { brightness, textOn } from '@/utils/contrast'

describe('brightness', () => {
  it('검정과 흰색이 양 끝이다', () => {
    expect(brightness('#000000')).toBe(0)
    expect(brightness('#ffffff')).toBe(1)
  })
})

describe('textOn', () => {
  it('파스텔 위에는 잉크색을 올린다', () => {
    expect(textOn('#efdd9a')).toBe('#17181c')
  })

  it('진한 색 위에는 흰색을 올린다', () => {
    expect(textOn('#3b82f6')).toBe('#ffffff')
  })

  it('파스텔 팔레트는 전부 잉크색으로 읽힌다', () => {
    for (const swatch of PALETTE) {
      expect(textOn(swatch)).toBe('#17181c')
    }
  })
})

