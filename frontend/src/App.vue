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

/** 비밀번호를 넣어 둔 이름들. 상단 배지로 보여 준다. */
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

/** 목록 위에 폼이 겹쳐 뜨지 않도록 목록을 접고 폼을 연다. */
function addFromList(memberId: number) {
  showMyList.value = false
  openNewSchedule(memberId)
}

function editFromList(schedule: Schedule) {
  showMyList.value = false
  openBlock(schedule)
}

function toggleAdmin() {
  if (store.isAdmin) {
    store.lockAdmin()
  } else {
    unlockMode.value = 'admin'
  }
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
  <div class="shell">
    <header class="bar">
      <h1>동아리 주간 시간표</h1>
      <span class="sub">매주 반복되는 일정만</span>

      <span class="spacer" />

      <button
        type="button"
        class="btn"
        @click="memberDialog = { mode: 'create' }"
      >
        이름 등록
      </button>
      <button type="button" class="btn" @click="showMyList = true">
        내 일정
      </button>

      <span class="divider" />

      <button
        v-for="id in unlockedIds"
        :key="`badge-${id}`"
        type="button"
        class="badge"
        :title="`${store.memberById(id)?.name} 이름과 비밀번호 수정`"
        @click="memberDialog = { mode: 'edit', memberId: id }"
      >
        {{ store.memberById(id)?.name }}
      </button>
      <button
        v-if="unlockedIds.length === 0"
        type="button"
        class="btn"
        @click="unlockMode = 'member'"
      >
        내 이름 확인
      </button>
      <button
        v-else
        type="button"
        class="btn btn--quiet btn--sm"
        @click="store.lockAll()"
      >
        잠그기
      </button>

      <button
        v-if="store.isAdmin"
        type="button"
        class="btn"
        @click="showCategories = true"
      >
        카테고리
      </button>
      <button
        type="button"
        class="btn"
        :class="{ 'btn--primary': store.isAdmin }"
        @click="toggleAdmin"
      >
        관리자
      </button>
    </header>

    <ErrorBanner />

    <div class="body">
      <MemberPanel />

      <div class="main">
        <ScheduleGrid
          :members="store.selectedMembers"
          :schedules="store.visibleSchedules"
          :paused="anyDialogOpen"
          @select="openBlock"
        />
      </div>
    </div>

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
      @create="addFromList"
      @edit="editFromList"
    />

    <ScheduleDialog
      v-if="scheduleDialog"
      :member-id="scheduleDialog.memberId"
      :schedule="scheduleDialog.schedule"
      @close="scheduleDialog = null"
    />
  </div>
</template>

<style scoped>
.shell {
  max-width: 1560px;
  margin: 0 auto;
  padding: 14px 20px 24px;
}

.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--rule);
}

h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.sub {
  font-size: 11.5px;
  color: var(--mute);
}

.spacer {
  flex: 1;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--rule-strong);
  margin: 0 4px;
}

.badge {
  font: inherit;
  font-weight: 650;
  padding: 5px 12px;
  border: 1px solid var(--ink);
  border-radius: 999px;
  background: var(--ink);
  color: var(--paper);
  cursor: pointer;
}

.badge:hover {
  background: #000;
}

.body {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.main {
  flex: 1;
  min-width: 0;
}

@media (max-width: 860px) {
  .shell {
    padding: 12px 12px 20px;
  }

  .body {
    flex-direction: column;
    /* 세로로 쌓이면 flex-start 는 가로 정렬이 되어 자식이 내용 폭으로 줄어든다. */
    align-items: stretch;
    gap: 14px;
  }

  .spacer {
    flex: 0 0 100%;
  }
}
</style>
