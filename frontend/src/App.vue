<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CategoryEditor from '@/components/CategoryEditor.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import MemberDialog from '@/components/MemberDialog.vue'
import MemberPanel from '@/components/MemberPanel.vue'
import MyScheduleList from '@/components/MyScheduleList.vue'
import ScheduleDialog from '@/components/ScheduleDialog.vue'
import ScheduleGrid from '@/components/ScheduleGrid.vue'
import UnlockDialog from '@/components/UnlockDialog.vue'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'

const store = useBoardStore()

const unlockMode = ref<'member' | 'admin' | null>(null)
const memberDialog = ref<{ mode: 'create' | 'edit'; memberId?: number } | null>(
  null,
)
const scheduleDialog = ref<{ memberId: number; schedule?: Schedule } | null>(null)
const showMyList = ref(false)
const showCategories = ref(false)

/** 잠금 해제해 둔 이름들. 관리자와 무관하게 "내 정보" 버튼용이다. */
const unlockedIds = computed(() => Object.keys(store.unlocked).map(Number))

/** 입력 중인 내용이 날아가지 않도록 다이얼로그가 열려 있으면 갱신을 미룬다. */
const anyDialogOpen = computed(
  () =>
    unlockMode.value !== null ||
    memberDialog.value !== null ||
    scheduleDialog.value !== null ||
    showMyList.value ||
    showCategories.value,
)

function openBlock(schedule: Schedule) {
  scheduleDialog.value = { memberId: schedule.member_id, schedule }
}

function openNewSchedule(memberId: number) {
  scheduleDialog.value = { memberId }
}

const POLL_MS = 15_000
let timer: number | undefined

function refreshIfIdle() {
  if (document.visibilityState !== 'visible' || anyDialogOpen.value) {
    return
  }
  void store.fetchBoard()
}

onMounted(() => {
  store.restore()
  void store.fetchBoard()
  timer = window.setInterval(refreshIfIdle, POLL_MS)
  document.addEventListener('visibilitychange', refreshIfIdle)
})

onUnmounted(() => {
  if (timer !== undefined) {
    window.clearInterval(timer)
  }
  document.removeEventListener('visibilitychange', refreshIfIdle)
})
</script>

<template>
  <main class="app">
    <h1>동아리 주간 시간표</h1>

    <div class="toolbar">
      <button type="button" @click="showCategories = true">카테고리 관리</button>
      <button type="button" @click="memberDialog = { mode: 'create' }">
        이름 등록
      </button>
      <button
        v-for="id in unlockedIds"
        :key="`info-${id}`"
        type="button"
        @click="memberDialog = { mode: 'edit', memberId: id }"
      >
        {{ store.memberById(id)?.name }} 정보
      </button>
      <button type="button" @click="showMyList = true">내 일정</button>

      <span class="spacer" />

      <button type="button" @click="unlockMode = 'member'">
        내 이름 잠금 해제
      </button>
      <button type="button" @click="unlockMode = 'admin'">
        {{ store.isAdmin ? '관리자 모드 켜짐' : '관리자 모드' }}
      </button>
      <button
        v-if="store.isAdmin || unlockedIds.length > 0"
        type="button"
        @click="store.lockAll()"
      >
        잠그기
      </button>
    </div>

    <div class="toolbar">
      <button type="button" @click="store.selectAll()">전체 보기</button>
      <button type="button" @click="store.clearSelection()">선택 해제</button>
      <span v-if="store.loading" class="muted">불러오는 중…</span>
    </div>

    <ErrorBanner />

    <MemberPanel />

    <ScheduleGrid
      :members="store.selectedMembers"
      :schedules="store.visibleSchedules"
      @select="openBlock"
    />

    <CategoryEditor v-if="showCategories" @close="showCategories = false" />

    <UnlockDialog
      v-if="unlockMode"
      :mode="unlockMode"
      @close="unlockMode = null"
    />

    <MemberDialog
      v-if="memberDialog"
      :mode="memberDialog.mode"
      :member-id="memberDialog.memberId"
      @close="memberDialog = null"
    />

    <MyScheduleList
      v-if="showMyList"
      @close="showMyList = false"
      @create="openNewSchedule"
      @edit="openBlock"
    />

    <ScheduleDialog
      v-if="scheduleDialog"
      :member-id="scheduleDialog.memberId"
      :schedule="scheduleDialog.schedule"
      @close="scheduleDialog = null"
    />
  </main>
</template>

<style scoped>
.app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
}

h1 {
  font-size: 20px;
  margin: 0 0 12px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.toolbar button {
  padding: 6px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
  font-size: 13px;
}

.spacer {
  flex: 1;
}

.muted {
  color: var(--muted);
  font-size: 13px;
}
</style>
