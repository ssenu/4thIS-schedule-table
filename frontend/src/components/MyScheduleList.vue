<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { slotToTime } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{
  close: []
  create: [memberId: number]
  edit: [schedule: Schedule]
}>()

const store = useBoardStore()

/** 관리자는 모두, 그 밖에는 비밀번호를 넣어 둔 본인만 고를 수 있다. */
const editableIds = computed(() =>
  store.isAdmin
    ? store.orderedMembers.map((member) => member.id)
    : Object.keys(store.unlocked).map(Number),
)

const targetId = ref<number | null>(
  store.activeMemberId ?? editableIds.value[0] ?? null,
)

const rows = computed(() =>
  targetId.value === null ? [] : store.schedulesOf(targetId.value),
)

const pendingDelete = ref<number | null>(null)
const message = ref('')
const busy = ref(false)

async function remove(schedule: Schedule) {
  message.value = ''
  busy.value = true
  try {
    await api.deleteSchedule(schedule.id, store.credentialsFor(schedule.member_id))
    await store.fetchBoard()
    pendingDelete.value = null
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '지우지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog title="내 일정" wide @close="emit('close')">
    <p v-if="editableIds.length === 0" class="notice notice--quiet">
      먼저 상단에서 내 이름을 확인해 주세요.
    </p>

    <template v-else>
      <label v-if="editableIds.length > 1" class="field picker">
        <span>대상</span>
        <select v-model.number="targetId" class="select">
          <option v-for="id in editableIds" :key="id" :value="id">
            {{ store.memberById(id)?.name }}
          </option>
        </select>
      </label>

      <p v-if="rows.length === 0" class="notice notice--quiet">
        아직 넣은 일정이 없습니다.
      </p>

      <ol v-else class="rows">
        <li v-for="row in rows" :key="row.id">
          <span class="day">{{ DAY_NAMES[row.day_of_week] }}</span>
          <span class="clock">
            {{ slotToTime(row.start_slot) }}–{{ slotToTime(row.end_slot) }}
          </span>
          <span class="what">{{ row.title }}</span>

          <template v-if="pendingDelete === row.id">
            <button
              type="button"
              class="btn btn--sm"
              @click="pendingDelete = null"
            >
              그만두기
            </button>
            <button
              type="button"
              class="btn btn--sm btn--fill-danger"
              :disabled="busy"
              @click="remove(row)"
            >
              지웁니다
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn btn--sm" @click="emit('edit', row)">
              수정
            </button>
            <button
              type="button"
              class="btn btn--sm btn--danger"
              @click="pendingDelete = row.id"
            >
              삭제
            </button>
          </template>
        </li>
      </ol>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <div class="row-end foot">
        <span class="spacer" />
        <button
          v-if="targetId !== null"
          type="button"
          class="btn btn--primary"
          @click="emit('create', targetId)"
        >
          일정 추가
        </button>
      </div>
    </template>
  </BaseDialog>
</template>

<style scoped>
.picker {
  flex-direction: row;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.picker > span {
  flex: 0 0 auto;
}

.picker .select {
  width: auto;
}

/* 한 줄이 곧 "무슨 요일 몇 시부터 몇 시까지 무슨 일정"이라는 문장이다. */
.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--rule);
}

.rows li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 2px;
  border-bottom: 1px solid var(--rule);
}

.day {
  flex: 0 0 16px;
  font-weight: 700;
}

.clock {
  flex: 0 0 96px;
  font-family: var(--mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--mute);
}

.what {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.foot {
  margin-top: 16px;
}
</style>
