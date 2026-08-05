<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import CategoryEditor from '@/components/CategoryEditor.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import GateEditor from '@/components/GateEditor.vue'
import GateScreen from '@/components/GateScreen.vue'
import MemberDialog from '@/components/MemberDialog.vue'
import MemberPanel from '@/components/MemberPanel.vue'
import MyScheduleList from '@/components/MyScheduleList.vue'
import ScheduleDialog from '@/components/ScheduleDialog.vue'
import ScheduleGrid from '@/components/ScheduleGrid.vue'
import UnlockDialog from '@/components/UnlockDialog.vue'
import { api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { COLOR_MODE_LABEL, nextColorMode } from '@/utils/blockColor'

const store = useBoardStore()

/** 지금 시간표를 고치고 있는 사람. 없으면 보기만 하는 상태다. */
const editingMemberId = ref<number | null>(null)

const unlockFor = ref<{ mode: 'member' | 'admin'; memberId?: number } | null>(
  null,
)
const memberDialog = ref<{ mode: 'create' | 'edit'; memberId?: number } | null>(
  null,
)
const scheduleDialog = ref<{
  memberId: number
  schedule?: Schedule
  preset?: { day: number; start: number; end: number }
} | null>(null)
const showMyList = ref(false)
const showCategories = ref(false)
const showGate = ref(false)

/** 수정은 한 사람씩. 둘 이상 고른 채로는 누구 걸 고치는지 알 수 없다. */
const selectedOne = computed(() =>
  store.selectedIds.length === 1 ? store.selectedIds[0] : null,
)

const colorLabel = computed(() => COLOR_MODE_LABEL[store.colorMode])
const nextColorLabel = computed(
  () => COLOR_MODE_LABEL[nextColorMode(store.colorMode)],
)

const editingMember = computed(() =>
  editingMemberId.value === null ? null : store.memberById(editingMemberId.value),
)

const editHint = computed(() => {
  if (store.selectedIds.length === 0) {
    return '왼쪽에서 내 이름을 하나 고르세요'
  }
  if (store.selectedIds.length > 1) {
    return '이름을 하나만 고르면 수정할 수 있습니다'
  }
  return `${store.memberById(store.selectedIds[0])?.name ?? ''} 시간표 수정`
})

/** 입력 중인 내용이 날아가지 않도록 다이얼로그가 열려 있으면 갱신을 미룬다. */
const anyDialogOpen = computed(
  () =>
    unlockFor.value !== null ||
    memberDialog.value !== null ||
    scheduleDialog.value !== null ||
    showMyList.value ||
    showCategories.value ||
    showGate.value,
)

function startEditing() {
  const id = selectedOne.value
  if (id === null) {
    return
  }
  // 관리자는 이미 확인을 마쳤다. 그 밖에는 누를 때마다 비밀번호를 묻는다.
  if (store.isAdmin) {
    editingMemberId.value = id
  } else {
    unlockFor.value = { mode: 'member', memberId: id }
  }
}

/** 수정을 끝내며 들고 있던 비밀번호를 버린다. 다음에 고치려면 다시 넣어야 한다. */
function endEditing() {
  if (editingMemberId.value !== null) {
    store.forgetMember(editingMemberId.value)
    editingMemberId.value = null
  }
}

function toggleAdmin() {
  if (store.isAdmin) {
    store.lockAdmin()
    // 관리자 권한으로 고치던 중이었다면 권한이 사라지므로 함께 끝낸다.
    endEditing()
  } else {
    unlockFor.value = { mode: 'admin' }
  }
}

// 고른 사람이 달라지면 누구를 고치는 중인지 흐려진다. 수정 모드를 접는다.
watch(
  () => [...store.selectedIds],
  (ids) => {
    if (
      editingMemberId.value !== null &&
      !(ids.length === 1 && ids[0] === editingMemberId.value)
    ) {
      endEditing()
    }
  },
)

function openBlock(schedule: Schedule) {
  scheduleDialog.value = { memberId: schedule.member_id, schedule }
}

/** 격자를 끌어서 만든 자리. 요일과 시간이 채워진 폼이 열린다. */
function onDraft(value: {
  memberId: number
  day: number
  start: number
  end: number
}) {
  scheduleDialog.value = {
    memberId: value.memberId,
    preset: { day: value.day, start: value.start, end: value.end },
  }
}

interface Placement {
  schedule: Schedule
  day: number
  start: number
  end: number
}

/**
 * 잡아 옮긴 자리를 그대로 저장한다.
 *
 * 폼으로 한 번 더 확인받지 않는다 — 이미 있는 일정을 옮기는 것이고,
 * 마음에 들지 않으면 다시 잡아 옮기면 된다.
 */
async function place(v: Placement, duplicate: boolean) {
  const creds = store.credentialsFor(v.schedule.member_id)
  const where = { day_of_week: v.day, start_slot: v.start, end_slot: v.end }
  try {
    if (duplicate) {
      await api.createSchedule(
        {
          member_id: v.schedule.member_id,
          title: v.schedule.title,
          color: v.schedule.color,
          ...where,
        },
        creds,
      )
    } else {
      await api.updateSchedule(v.schedule.id, where, creds)
    }
    await store.fetchBoard()
  } catch (err) {
    store.reportError(err)
  }
}

function onMove(v: Placement) {
  void place(v, false)
}

function onCopy(v: Placement) {
  void place(v, true)
}

function onClash() {
  store.error = '이미 있는 일정과 겹쳐서 놓을 수 없습니다.'
}

/** 목록 위에 폼이 겹쳐 뜨지 않도록 목록을 접고 폼을 연다. */
function addFromList(memberId: number) {
  showMyList.value = false
  scheduleDialog.value = { memberId }
}

function editFromList(schedule: Schedule) {
  showMyList.value = false
  openBlock(schedule)
}

const POLL_MS = 15_000
let timer: number | undefined

function refreshIfIdle() {
  if (
    !store.gateOpen ||
    document.visibilityState !== 'visible' ||
    anyDialogOpen.value
  ) {
    return
  }
  void store.fetchBoard()
}

onMounted(() => {
  store.restore()
  void store.loadGate()
  // 저장된 비밀번호가 맞으면 첫 화면이 깜빡이지 않는다. 틀리면 스토어가
  // 게이트 오류를 알아보고 문 앞으로 돌려보낸다.
  if (store.gateOpen) {
    void store.fetchBoard()
  }
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
  <!--
    문구를 받기 전에는 첫 화면을 그리지 않는다. 기본 문구로 먼저 그리면
    관리자가 고쳐 둔 문구로 바뀌면서 눈에 띄게 깜빡인다.
  -->
  <GateScreen v-if="!store.gateOpen && store.gateLoaded" />

  <div v-else-if="store.gateOpen" class="shell">
    <header class="bar">
      <h1>동아리 주간 시간표</h1>
      <span class="sub">명지전문대학 4thIS 동아리원 시간표</span>

      <span class="spacer" />

      <template v-if="editingMember">
        <button
          type="button"
          class="btn btn--icon"
          :title="`색 기준: ${colorLabel} — 누르면 ${nextColorLabel}`"
          :aria-label="`색 기준 ${colorLabel}, 눌러서 ${nextColorLabel}로`"
          @click="store.cycleColorMode()"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <circle cx="5.6" cy="8" r="3.4" fill="currentColor" opacity="0.3" />
            <circle cx="8" cy="8" r="3.4" fill="currentColor" opacity="0.55" />
            <circle cx="10.4" cy="8" r="3.4" fill="currentColor" opacity="0.85" />
          </svg>
          {{ colorLabel }}
        </button>
        <span class="now">{{ editingMember.name }} 수정 중</span>
        <button type="button" class="btn" @click="showMyList = true">
          일정 관리
        </button>
        <button
          type="button"
          class="btn"
          @click="memberDialog = { mode: 'edit', memberId: editingMember.id }"
        >
          이름 수정
        </button>
        <button type="button" class="btn btn--primary" @click="endEditing">
          완료
        </button>
      </template>

      <template v-else>
        <button
          type="button"
          class="btn btn--icon"
          :title="`색 기준: ${colorLabel} — 누르면 ${nextColorLabel}`"
          :aria-label="`색 기준 ${colorLabel}, 눌러서 ${nextColorLabel}로`"
          @click="store.cycleColorMode()"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <circle cx="5.6" cy="8" r="3.4" fill="currentColor" opacity="0.3" />
            <circle cx="8" cy="8" r="3.4" fill="currentColor" opacity="0.55" />
            <circle cx="10.4" cy="8" r="3.4" fill="currentColor" opacity="0.85" />
          </svg>
          {{ colorLabel }}
        </button>
        <button
          type="button"
          class="btn"
          @click="memberDialog = { mode: 'create' }"
        >
          이름 등록
        </button>
        <button
          type="button"
          class="btn btn--icon"
          :disabled="selectedOne === null"
          :title="editHint"
          @click="startEditing"
        >
          <svg
            viewBox="0 0 16 16"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M11.3 2.2 13.8 4.7 5.5 13 2.2 13.8 3 10.5Z" />
            <path d="M10.1 3.4 12.6 5.9" />
          </svg>
          수정
        </button>
      </template>

      <span class="divider" />

      <button
        v-if="store.isAdmin"
        type="button"
        class="btn"
        @click="showCategories = true"
      >
        카테고리
      </button>
      <button
        v-if="store.isAdmin"
        type="button"
        class="btn"
        @click="showGate = true"
      >
        입장 설정
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
        <p v-if="editingMember" class="guide">
          격자에서 <b>{{ editingMember.name }}</b> 칸을 끌면 그 시간에 일정을
          만듭니다. 이미 있는 일정은 눌러서 고칩니다.
        </p>

        <ScheduleGrid
          :members="store.selectedMembers"
          :schedules="store.visibleSchedules"
          :paused="anyDialogOpen"
          :editing-member-id="editingMemberId"
          :color-mode="store.colorMode"
          @select="openBlock"
          @draft="onDraft"
          @move="onMove"
          @copy="onCopy"
          @clash="onClash"
        />
      </div>
    </div>

    <CategoryEditor v-if="showCategories" @close="showCategories = false" />

    <GateEditor v-if="showGate" @close="showGate = false" />

    <UnlockDialog
      v-if="unlockFor"
      :mode="unlockFor.mode"
      :member-id="unlockFor.memberId"
      @close="unlockFor = null"
      @unlocked="(id) => (editingMemberId = id)"
    />

    <MemberDialog
      v-if="memberDialog"
      :mode="memberDialog.mode"
      :member-id="memberDialog.memberId"
      @close="memberDialog = null"
    />

    <MyScheduleList
      v-if="showMyList && editingMemberId !== null"
      :member-id="editingMemberId"
      @close="showMyList = false"
      @create="addFromList"
      @edit="editFromList"
    />

    <ScheduleDialog
      v-if="scheduleDialog"
      :member-id="scheduleDialog.memberId"
      :schedule="scheduleDialog.schedule"
      :preset="scheduleDialog.preset"
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

.now {
  font-weight: 700;
  letter-spacing: 0.01em;
}

.guide {
  margin: 0 0 9px;
  font-size: 12px;
  color: var(--mute);
}

.guide b {
  color: var(--ink);
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
