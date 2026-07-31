import { DAY_NAMES } from '@/constants'

/** 남은 폭에 요일이 몇 개나 들어가는지. 최소 하나는 보여 준다. */
export function daysPerPage(
  available: number,
  memberCount: number,
  minColumn: number,
): number {
  if (memberCount <= 0 || minColumn <= 0) {
    return DAY_NAMES.length
  }
  const dayWidth = memberCount * minColumn
  const fit = Math.floor(available / dayWidth)
  return Math.min(DAY_NAMES.length, Math.max(1, fit))
}

/**
 * 일주일을 페이지로 나눈다.
 *
 * 들어가는 만큼 앞에서부터 잘라 내면 마지막 페이지에 하루만 남는 일이 생긴다.
 * 필요한 페이지 수를 먼저 세고 고르게 나눠서, 세 개씩 들어가면 3·2·2 로,
 * 네 개씩 들어가면 4·3 으로 갈린다.
 */
export function splitIntoPages(perPage: number): number[][] {
  const total = DAY_NAMES.length
  const pageCount = Math.max(1, Math.ceil(total / Math.max(1, perPage)))
  const base = Math.floor(total / pageCount)
  const extra = total % pageCount

  const pages: number[][] = []
  let day = 0
  for (let index = 0; index < pageCount; index += 1) {
    const size = base + (index < extra ? 1 : 0)
    pages.push(Array.from({ length: size }, (_, offset) => day + offset))
    day += size
  }
  return pages
}

/** "월–수" 또는 하루뿐이면 "일". */
export function pageLabel(days: number[]): string {
  if (days.length === 0) {
    return ''
  }
  const first = DAY_NAMES[days[0]]
  const last = DAY_NAMES[days[days.length - 1]]
  return first === last ? first : `${first}–${last}`
}
