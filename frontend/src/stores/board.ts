import { defineStore } from 'pinia'
import { ApiError, api, setGatePassword } from '@/api/client'
import { DEFAULT_GATE_INTRO, DEFAULT_GATE_TITLE } from '@/constants'
import type { Category, Credentials, Member, Schedule } from '@/types'
import type { ColorMode } from '@/utils/blockColor'
import { nextColorMode } from '@/utils/blockColor'

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
  /**
   * memberId -> 4자리 비밀번호. 수정하는 동안만 들고 있고 저장하지 않는다.
   * 수정을 끝내면 지우므로, 다음에 고치려면 비밀번호를 다시 넣어야 한다.
   */
  unlocked: Record<number, string>
  adminPassword: string
  /** 입장 비밀번호를 넣고 사이트 안에 들어와 있는지. */
  gateOpen: boolean
  /**
   * 첫 화면 문구를 서버에서 받아 왔는지.
   *
   * 받기 전에 기본 문구로 화면을 그리면, 관리자가 문구를 고쳐 둔 경우
   * 기본 문구가 잠깐 떴다가 바뀌어 깜빡인다. 받을 때까지 그리지 않는다.
   */
  gateLoaded: boolean
  gateTitle: string
  gateIntro: string
  /** 유일하게 브라우저에 남기는 비밀번호. 개인·관리자 것은 남기지 않는다. */
  gatePassword: string
  /** 블록 색을 무엇으로 정할지. 보기 설정이라 브라우저에 남긴다. */
  colorMode: ColorMode
  /** 왼쪽 이름 목록을 접어 두었는지. 이것도 보기 설정이라 남긴다. */
  sideFolded: boolean
  error: string
  loading: boolean
}

/** 브라우저에 남기는 것은 무엇을 보고 있었는지뿐이다. 비밀번호는 남기지 않는다. */
interface Persisted {
  selectedIds?: number[]
  colorMode?: ColorMode
  sideFolded?: boolean
  gatePassword?: string
}

export const useBoardStore = defineStore('board', {
  state: (): BoardState => ({
    categories: [],
    members: [],
    schedules: [],
    selectedIds: [],
    unlocked: {},
    adminPassword: '',
    gateOpen: false,
    gateLoaded: false,
    // 진짜 문구는 서버에 있다. 여기서 흉내 내면 두 번 그려진다.
    gateTitle: '',
    gateIntro: '',
    gatePassword: '',
    colorMode: 'own',
    sideFolded: false,
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
        if (err instanceof ApiError && err.gateRequired) {
          // 문 앞으로 돌아가는 것이 이미 설명이다. 빨간 띠까지 띄우지 않는다.
          this.gateOpen = false
          this.gatePassword = ''
          setGatePassword('')
          this.error = ''
          this.persist()
          return
        }
        this.reportError(err)
      } finally {
        this.loading = false
      }
    },

    async loadGate() {
      try {
        const gate = await api.gate()
        this.gateTitle = gate.title
        this.gateIntro = gate.intro
      } catch {
        // 문구를 못 받아도 첫 화면은 떠야 한다. 비워 두면 비밀번호를
        // 넣을 칸조차 없이 빈 화면에 갇힌다.
        this.gateTitle = DEFAULT_GATE_TITLE
        this.gateIntro = DEFAULT_GATE_INTRO
      } finally {
        this.gateLoaded = true
      }
    },

    /** 첫 화면에서 넣은 비밀번호. 맞는지 서버에 물어본 뒤 받아들인다. */
    async enterGate(password: string) {
      await api.verifyGate(password)
      this.adoptGatePassword(password)
    },

    /**
     * 관리자가 방금 세운 비밀번호를 확인 없이 받아들인다.
     *
     * 서버가 200 을 준 값이라 다시 물어볼 이유가 없다. 한 번 더 물으면
     * 왕복이 늘고, 그 사이 옛 비밀번호를 들고 있는 창이 열려 폴링이
     * 끼어들면 방금 바꾼 본인이 문 밖으로 밀려난다.
     */
    adoptGatePassword(password: string) {
      this.gatePassword = password
      setGatePassword(password)
      this.gateOpen = true
      this.persist()
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

    lockAdmin() {
      this.adminPassword = ''
      this.persist()
    },

    /** 수정이 끝나면 들고 있던 비밀번호를 버린다. */
    forgetMember(id: number) {
      delete this.unlocked[id]
    },

    cycleColorMode() {
      this.colorMode = nextColorMode(this.colorMode)
      this.persist()
    },

    /** 왼쪽 이름 목록을 접었다 편다. 접으면 표가 그만큼 넓어진다. */
    toggleSide() {
      this.sideFolded = !this.sideFolded
      this.persist()
    },

    reportError(err: unknown) {
      this.error =
        err instanceof ApiError ? err.message : '알 수 없는 오류가 발생했습니다.'
    },

    persist() {
      const payload: Persisted = {
        selectedIds: this.selectedIds,
        colorMode: this.colorMode,
        sideFolded: this.sideFolded,
        gatePassword: this.gatePassword,
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
        this.colorMode = saved.colorMode ?? 'own'
        this.sideFolded = saved.sideFolded ?? false
        this.gatePassword = saved.gatePassword ?? ''
        setGatePassword(this.gatePassword)
        // 저장된 비밀번호가 맞는지는 첫 요청이 알려 준다. 맞으면 화면이
        // 깜빡이지 않고, 틀리면 그때 문 앞으로 돌아간다.
        this.gateOpen = this.gatePassword !== ''
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    },
  },
})
