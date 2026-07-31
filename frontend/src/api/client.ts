import type { Board, Category, Credentials, Member, Schedule } from '@/types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 관리자 자격이 있으면 그쪽만 보낸다. 서버도 관리자를 우선 판정한다.
 *
 * HTTP 헤더 값은 ASCII만 안전한데 관리자 비밀번호에는 한글이 들어갈 수 있어
 * 퍼센트 인코딩해서 싣는다. 서버는 urllib.parse.unquote 로 되돌린다.
 */
export function authHeaders(creds: Credentials = {}): Record<string, string> {
  if (creds.adminPassword) {
    return { 'X-Admin-Password': encodeURIComponent(creds.adminPassword) }
  }
  if (creds.memberId !== undefined && creds.memberPassword) {
    return {
      'X-Member-Id': String(creds.memberId),
      'X-Member-Password': encodeURIComponent(creds.memberPassword),
    }
  }
  return {}
}

/** FastAPI의 detail은 문자열이거나 검증 오류 배열이다. */
function extractDetail(data: unknown, status: number): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown }
      if (typeof first?.msg === 'string') {
        return first.msg.replace(/^Value error,\s*/, '')
      }
    }
  }
  return `요청이 실패했습니다. (${status})`
}

export async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; creds?: Credentials } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders(options.creds) }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없습니다.')
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    throw new ApiError(response.status, extractDetail(data, response.status))
  }
  return data as T
}

type VerifyBody = { scope: 'admin' } | { scope: 'member'; member_id: number }

export const api = {
  board: () => request<Board>('GET', '/api/board'),

  verify: (body: VerifyBody, creds: Credentials) =>
    request<{ ok: boolean }>('POST', '/api/auth/verify', { body, creds }),

  createCategory: (name: string, creds: Credentials) =>
    request<Category>('POST', '/api/categories', { body: { name }, creds }),

  renameCategory: (id: number, name: string, creds: Credentials) =>
    request<Category>('PATCH', `/api/categories/${id}`, { body: { name }, creds }),

  deleteCategory: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/categories/${id}`, { creds }),

  reorderCategories: (orderedIds: number[], creds: Credentials) =>
    request<{ ok: boolean }>('PUT', '/api/categories/order', {
      body: { ordered_ids: orderedIds },
      creds,
    }),

  createMember: (body: { name: string; category_id: number; password: string }) =>
    request<Member>('POST', '/api/members', { body }),

  updateMember: (
    id: number,
    body: { name?: string; password?: string; category_id?: number },
    creds: Credentials,
  ) => request<Member>('PATCH', `/api/members/${id}`, { body, creds }),

  deleteMember: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/members/${id}`, { creds }),

  reorderMembers: (categoryId: number, orderedIds: number[], creds: Credentials) =>
    request<{ ok: boolean }>('PUT', '/api/members/order', {
      body: { category_id: categoryId, ordered_ids: orderedIds },
      creds,
    }),

  createSchedule: (body: Omit<Schedule, 'id'>, creds: Credentials) =>
    request<Schedule>('POST', '/api/schedules', { body, creds }),

  updateSchedule: (
    id: number,
    body: Partial<Omit<Schedule, 'id' | 'member_id'>>,
    creds: Credentials,
  ) => request<Schedule>('PATCH', `/api/schedules/${id}`, { body, creds }),

  deleteSchedule: (id: number, creds: Credentials) =>
    request<void>('DELETE', `/api/schedules/${id}`, { creds }),
}
