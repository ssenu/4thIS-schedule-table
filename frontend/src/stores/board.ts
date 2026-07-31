import { defineStore } from 'pinia'
import { ApiError, api } from '@/api/client'
import type { Category, Credentials, Member, Schedule } from '@/types'

const STORAGE_KEY = 'club-schedule'

/** 카테고리 순서를 먼저, 그 안에서 멤버 순서를 따라 한 줄로 편다. */
export function orderMembers(
  categories: Category[],
  members: Member[],
): Member[] {
  const rank = new Map(categories.map((c) => [c.id, c.sort_order]))
  return [...members].sort(
    (a, b) =>
      (rank.get(a.category_id) ?? 0) - (rank.get(b.category_id) ?? 0) ||
      a.sort_order - b.sort_order ||
      a.id - b.id,
  )
}

interface BoardState {
  categories: Category[]
  members: Member[]
  schedules: Schedule[]
  selectedIds: number[]
  /** memberId -> 4자리 비밀번호. 잠금 해제한 사람만 들어 있다. */
  unlocked: Record<number, string>
  adminPassword: string
  /** "내 일정" 화면이 대상으로 삼는 멤버. */
  activeMemberId: number | null
  error: string
  loading: boolean
}

interface Persisted {
  selectedIds?: number[]
  unlocked?: Record<number, string>
  adminPassword?: string
  activeMemberId?: number | null
}

export const useBoardStore = defineStore('board', {
  state: (): BoardState => ({
    categories: [],
    members: [],
    schedules: [],
    selectedIds: [],
    unlocked: {},
    adminPassword: '',
    activeMemberId: null,
    error: '',
    loading: false,
  }),

  getters: {
    isAdmin: (state) => state.adminPassword !== '',

    sortedCategories: (state) =>
      [...state.categories].sort((a, b) => a.sort_order - b.sort_order),

    orderedMembers: (state) => orderMembers(state.categories, state.members),

    membersOf: (state) => (categoryId: number) =>
      state.members
        .filter((m) => m.category_id === categoryId)
        .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id),

    selectedMembers: (state) => {
      const chosen = new Set(state.selectedIds)
      return orderMembers(state.categories, state.members).filter((m) =>
        chosen.has(m.id),
      )
    },

    visibleSchedules: (state) => {
      const chosen = new Set(state.selectedIds)
      return state.schedules.filter((s) => chosen.has(s.member_id))
    },

    schedulesOf: (state) => (memberId: number) =>
      state.schedules
        .filter((s) => s.member_id === memberId)
        .sort(
          (a, b) => a.day_of_week - b.day_of_week || a.start_slot - b.start_slot,
        ),

    canEdit: (state) => (memberId: number) =>
      state.adminPassword !== '' || state.unlocked[memberId] !== undefined,

    credentialsFor:
      (state) =>
      (memberId?: number): Credentials => {
        if (state.adminPassword) {
          return { adminPassword: state.adminPassword }
        }
        if (memberId !== undefined && state.unlocked[memberId]) {
          return { memberId, memberPassword: state.unlocked[memberId] }
        }
        return {}
      },

    memberById: (state) => (id: number) =>
      state.members.find((m) => m.id === id) ?? null,
  },

  actions: {
    async fetchBoard() {
      this.loading = true
      try {
        const board = await api.board()
        this.categories = board.categories
        this.members = board.members
        this.schedules = board.schedules
        this.pruneSelection()
        this.error = ''
      } catch (err) {
        this.reportError(err)
      } finally {
        this.loading = false
      }
    },

    /** 서버에서 사라진 멤버를 선택·잠금 목록에서 걷어낸다. */
    pruneSelection() {
      const alive = new Set(this.members.map((m) => m.id))
      this.selectedIds = this.selectedIds.filter((id) => alive.has(id))
      for (const key of Object.keys(this.unlocked)) {
        if (!alive.has(Number(key))) {
          delete this.unlocked[Number(key)]
        }
      }
      if (this.activeMemberId !== null && !alive.has(this.activeMemberId)) {
        this.activeMemberId = null
      }
      this.persist()
    },

    toggleSelection(id: number) {
      const at = this.selectedIds.indexOf(id)
      if (at >= 0) {
        this.selectedIds.splice(at, 1)
      } else {
        this.selectedIds.push(id)
      }
      this.persist()
    },

    selectAll() {
      this.selectedIds = this.members.map((m) => m.id)
      this.persist()
    },

    clearSelection() {
      this.selectedIds = []
      this.persist()
    },

    async unlockMember(id: number, password: string) {
      await api.verify(
        { scope: 'member', member_id: id },
        { memberId: id, memberPassword: password },
      )
      this.unlocked[id] = password
      this.activeMemberId = id
      if (!this.selectedIds.includes(id)) {
        this.selectedIds.push(id)
      }
      this.persist()
    },

    async unlockAdmin(password: string) {
      await api.verify({ scope: 'admin' }, { adminPassword: password })
      this.adminPassword = password
      this.persist()
    },

    lockAll() {
      this.unlocked = {}
      this.adminPassword = ''
      this.activeMemberId = null
      this.persist()
    },

    reportError(err: unknown) {
      this.error =
        err instanceof ApiError ? err.message : '알 수 없는 오류가 발생했습니다.'
    },

    persist() {
      const payload: Persisted = {
        selectedIds: this.selectedIds,
        unlocked: this.unlocked,
        adminPassword: this.adminPassword,
        activeMemberId: this.activeMemberId,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    },

    restore() {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        return
      }
      try {
        const saved = JSON.parse(raw) as Persisted
        this.selectedIds = saved.selectedIds ?? []
        this.unlocked = saved.unlocked ?? {}
        this.adminPassword = saved.adminPassword ?? ''
        this.activeMemberId = saved.activeMemberId ?? null
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    },
  },
})
