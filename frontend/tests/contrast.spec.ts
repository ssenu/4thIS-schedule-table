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
  it('밝은 노랑 위에는 잉크색을 올린다', () => {
    expect(textOn('#eab308')).toBe('#17181c')
  })

  it('진한 파랑 위에는 흰색을 올린다', () => {
    expect(textOn('#3b82f6')).toBe('#ffffff')
  })

  it('팔레트의 모든 색에 답을 준다', () => {
    for (const swatch of PALETTE) {
      expect(['#17181c', '#ffffff']).toContain(textOn(swatch))
    }
  })
})
