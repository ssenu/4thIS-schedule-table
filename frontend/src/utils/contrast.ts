/**
 * 블록 색 위에 올릴 글자색을 고른다.
 *
 * 팔레트에는 노랑(#eab308)처럼 밝은 색이 있어서 전부 흰 글씨로 두면
 * 제목이 읽히지 않는다. 밝기를 재서 밝은 바탕에는 잉크색을 올린다.
 */

const INK = '#17181c'
const PAPER = '#ffffff'

/** 0(검정) ~ 1(흰색). 사람 눈의 채널별 민감도를 반영한 근사치다. */
export function brightness(hex: string): number {
  const value = hex.replace('#', '')
  const r = Number.parseInt(value.slice(0, 2), 16)
  const g = Number.parseInt(value.slice(2, 4), 16)
  const b = Number.parseInt(value.slice(4, 6), 16)
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255
}

export function textOn(hex: string): string {
  return brightness(hex) > 0.5 ? INK : PAPER
}
