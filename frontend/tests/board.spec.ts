import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { orderMembers, useBoardStore } from '@/stores/board'
import type { Category, Member, Schedule } from '@/types'

const CATEGORIES: Category[] = [
  { id: 10, name: '1학년', sort_order: 0 },
  { id: 20, name: '2학년', sort_order: 1 },
]

const MEMBERS: Member[] = [
  { id: 3, name: '민수', category_id: 20, sort_order: 0 },
  { id: 1, name: '철수', category_id: 10, sort_order: 1 },
  { id: 2, name: '영희', category_id: 10, sort_order: 0 },
]

const SCHEDULES: Schedule[] = [
  {
    id: 100,
    member_id: 1,
    day_of_week: 2,
    start_slot: 6,
    end_slot: 14,
    title: '전공수업',
    color: '#ef4444',
  },
  {
    id: 101,
    member_id: 1,
    day_of_week: 0,
    start_slot: 20,
    end_slot: 24,
    title: '알바',
    color: '#3b82f6',
  },
  {
    id: 102,
    member_id: 3,
    day_of_week: 0,
    start_slot: 6,
    end_slot: 8,
    title: '교양',
    color: '#22c55e',
  },
]

function seeded() {
  const store = useBoardStore()
  store.categories = CATEGORIES
  store.members = MEMBERS
  store.schedules = SCHEDULES
  return store
}

function stubBoard(members: Member[], schedules: Schedule[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: () =>
        Promise.resolve(
          JSON.stringify({ categories: CATEGORIES, members, schedules }),
        ),
    }),
  )
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('orderMembers', () => {
  it('카테고리 순서 다음에 카테고리 안 순서로 늘어놓는다', () => {
    const names = orderMembers(CATEGORIES, MEMBERS).map((m) => m.name)
    expect(names).toEqual(['영희', '철수', '민수'])
  })
})

describe('선택', () => {
  it('토글로 켜고 끈다', () => {
    const store = seeded()
    store.toggleSelection(1)
    expect(store.selectedIds).toEqual([1])
    store.toggleSelection(1)
    expect(store.selectedIds).toEqual([])
  })

  it('선택된 멤버는 표시 순서를 따른다', () => {
    const store = seeded()
    store.toggleSelection(3)
    store.toggleSelection(2)
    expect(store.selectedMembers.map((m) => m.name)).toEqual(['영희', '민수'])
  })

  it('선택된 사람의 일정만 보인다', () => {
    const store = seeded()
    store.toggleSelection(1)
    expect(store.visibleSchedules.map((s) => s.id)).toEqual([100, 101])
  })

  it('전체 선택과 해제', () => {
    const store = seeded()
    store.selectAll()
    expect(store.selectedIds).toHaveLength(3)
    store.clearSelection()
    expect(store.selectedIds).toEqual([])
  })
})

describe('권한', () => {
  it('잠금 해제한 본인만 편집할 수 있다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    expect(store.canEdit(1)).toBe(true)
    expect(store.canEdit(2)).toBe(false)
  })

  it('관리자는 전부 편집할 수 있다', () => {
    const store = seeded()
    store.adminPassword = 'secret'
    expect(store.canEdit(2)).toBe(true)
    expect(store.isAdmin).toBe(true)
  })

  it('자격 정보는 관리자를 우선한다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    store.adminPassword = 'secret'
    expect(store.credentialsFor(1)).toEqual({ adminPassword: 'secret' })
  })

  it('잠금 해제한 멤버의 자격을 만든다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    expect(store.credentialsFor(1)).toEqual({
      memberId: 1,
      memberPassword: '1234',
    })
  })

  it('아무 자격도 없으면 빈 객체다', () => {
    const store = seeded()
    expect(store.credentialsFor(1)).toEqual({})
  })
})

describe('내 일정 목록', () => {
  it('요일 다음 시작 시각 순으로 정렬한다', () => {
    const store = seeded()
    expect(store.schedulesOf(1).map((s) => s.id)).toEqual([101, 100])
  })
})

describe('저장과 복원', () => {
  it('무엇을 보고 있었는지는 남는다', () => {
    const store = seeded()
    store.toggleSelection(1)

    setActivePinia(createPinia())
    const revived = useBoardStore()
    revived.restore()

    expect(revived.selectedIds).toEqual([1])
  })

  it('비밀번호는 브라우저에 남기지 않는다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234' }
    store.adminPassword = 'secret'
    store.toggleSelection(1)

    expect(localStorage.getItem('club-schedule') ?? '').not.toContain('1234')
    expect(localStorage.getItem('club-schedule') ?? '').not.toContain('secret')

    setActivePinia(createPinia())
    const revived = useBoardStore()
    revived.restore()

    expect(revived.unlocked).toEqual({})
    expect(revived.adminPassword).toBe('')
  })

  it('저장된 것이 없어도 문제없다', () => {
    const store = useBoardStore()
    store.restore()
    expect(store.selectedIds).toEqual([])
  })
})

describe('forgetMember', () => {
  it('수정이 끝나면 들고 있던 비밀번호를 버린다', () => {
    const store = seeded()
    store.unlocked = { 1: '1234', 2: '1111' }
    store.forgetMember(1)
    expect(store.canEdit(1)).toBe(false)
    expect(store.canEdit(2)).toBe(true)
  })
})

describe('fetchBoard', () => {
  it('서버 응답을 상태에 넣는다', async () => {
    stubBoard(MEMBERS, SCHEDULES)
    const store = useBoardStore()
    await store.fetchBoard()
    expect(store.members).toHaveLength(3)
    expect(store.error).toBe('')
    vi.unstubAllGlobals()
  })

  it('사라진 멤버의 선택과 잠금을 정리한다', async () => {
    const store = seeded()
    store.toggleSelection(1)
    store.unlocked = { 1: '1234' }

    stubBoard([MEMBERS[0]], [])
    await store.fetchBoard()
    expect(store.selectedIds).toEqual([])
    expect(store.unlocked).toEqual({})
    vi.unstubAllGlobals()
  })

  it('실패하면 오류 메시지를 남긴다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    const store = useBoardStore()
    await store.fetchBoard()
    expect(store.error).toBe('서버에 연결할 수 없습니다.')
    vi.unstubAllGlobals()
  })
})
