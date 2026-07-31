import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, authHeaders, request } from '@/api/client'

function stubFetch(status: number, body: unknown) {
  const text = body === null ? '' : JSON.stringify(body)
  const fake = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(text),
  })
  vi.stubGlobal('fetch', fake)
  return fake
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('authHeaders', () => {
  it('자격이 없으면 헤더도 없다', () => {
    expect(authHeaders()).toEqual({})
    expect(authHeaders({})).toEqual({})
  })

  it('멤버 자격을 헤더로 만든다', () => {
    expect(authHeaders({ memberId: 7, memberPassword: '1234' })).toEqual({
      'X-Member-Id': '7',
      'X-Member-Password': '1234',
    })
  })

  it('관리자 자격이 멤버 자격보다 우선한다', () => {
    const headers = authHeaders({
      adminPassword: 'secret',
      memberId: 7,
      memberPassword: '1234',
    })
    expect(headers).toEqual({ 'X-Admin-Password': 'secret' })
  })

  it('비ASCII 비밀번호를 퍼센트 인코딩한다', () => {
    // 헤더 값은 ASCII만 안전하다. 서버가 unquote로 되돌린다.
    const headers = authHeaders({ adminPassword: '관리자비밀' })
    expect(headers['X-Admin-Password']).toBe(encodeURIComponent('관리자비밀'))
  })
})

describe('request', () => {
  it('JSON 본문을 돌려준다', async () => {
    stubFetch(200, { categories: [], members: [], schedules: [] })
    const board = await request('GET', '/api/board')
    expect(board).toEqual({ categories: [], members: [], schedules: [] })
  })

  it('204에는 본문이 없다', async () => {
    stubFetch(204, null)
    await expect(request('DELETE', '/api/schedules/1')).resolves.toBeUndefined()
  })

  it('본문이 있으면 Content-Type을 붙인다', async () => {
    const fake = stubFetch(201, { id: 1 })
    await request('POST', '/api/categories', { body: { name: '4학년' } })
    const [, init] = fake.mock.calls[0]
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe(JSON.stringify({ name: '4학년' }))
  })

  it('인증 헤더를 실어 보낸다', async () => {
    const fake = stubFetch(200, {})
    await request('PATCH', '/api/members/7', {
      body: { name: '철수' },
      creds: { memberId: 7, memberPassword: '1234' },
    })
    const [, init] = fake.mock.calls[0]
    expect(init.headers['X-Member-Id']).toBe('7')
  })

  it('서버 오류 메시지를 그대로 전한다', async () => {
    stubFetch(409, { detail: "월 09:00~13:00 '전공수업'과(와) 겹칩니다." })
    await expect(request('POST', '/api/schedules')).rejects.toMatchObject({
      status: 409,
      message: "월 09:00~13:00 '전공수업'과(와) 겹칩니다.",
    })
  })

  it('검증 오류의 첫 메시지를 꺼낸다', async () => {
    stubFetch(422, {
      detail: [{ msg: 'Value error, 허용되지 않은 색상입니다.', loc: ['body'] }],
    })
    await expect(request('POST', '/api/schedules')).rejects.toMatchObject({
      message: '허용되지 않은 색상입니다.',
    })
  })

  it('네트워크 실패는 status 0이다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(request('GET', '/api/board')).rejects.toMatchObject({
      status: 0,
    })
  })

  it('던지는 것은 ApiError다', async () => {
    stubFetch(403, { detail: '관리자만 할 수 있습니다.' })
    await expect(request('DELETE', '/api/categories/1')).rejects.toBeInstanceOf(
      ApiError,
    )
  })
})
