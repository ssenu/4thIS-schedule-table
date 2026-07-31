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

/** 관리자는 모두, 일반 사용자는 잠금 해제한 본인만 고를 수 있다. */
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
    message.value = err instanceof ApiError ? err.message : '삭제하지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog title="내 일정" @close="emit('close')">
    <p v-if="editableIds.length === 0" class="hint">
      먼저 이름을 잠금 해제해 주세요.
    </p>

    <template v-else>
      <label v-if="editableIds.length > 1" class="picker">
        대상
        <select v-model.number="targetId">
          <option v-for="id in editableIds" :key="id" :value="id">
            {{ store.memberById(id)?.name }}
          </option>
        </select>
      </label>

      <p v-if="rows.length === 0" class="hint">아직 등록된 일정이 없습니다.</p>

      <ol v-else class="rows">
        <li v-for="row in rows" :key="row.id">
          <span class="day">{{ DAY_NAMES[row.day_of_week] }}</span>
          <span class="time">
            {{ slotToTime(row.start_slot) }} ~ {{ slotToTime(row.end_slot) }}
          </span>
          <span class="title">{{ row.title }}</span>

          <template v-if="pendingDelete === row.id">
            <button type="button" @click="pendingDelete = null">아니오</button>
            <button
              type="button"
              class="danger"
              :disabled="busy"
              @click="remove(row)"
            >
              지웁니다
            </button>
          </template>
          <template v-else>
            <button type="button" @click="emit('edit', row)">수정</button>
            <button type="button" class="danger" @click="pendingDelete = row.id">
              삭제
            </button>
          </template>
        </li>
      </ol>

      <p v-if="message" class="message">{{ message }}</p>

      <div class="actions">
        <button
          v-if="targetId !== null"
          type="button"
          class="primary"
          @click="emit('create', targetId)"
        >
          + 일정 추가
        </button>
      </div>
    </template>
  </BaseDialog>
</template>

<style scoped>
.picker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--muted);
}

.picker select {
  padding: 6px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  color: var(--text);
}

.hint {
  margin: 8px 0;
  color: var(--muted);
  font-size: 13px;
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--surface-alt);
  font-size: 13px;
}

.day {
  flex: 0 0 20px;
  font-weight: 700;
}

.time {
  flex: 0 0 120px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rows button {
  padding: 4px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 5px;
  background: var(--surface);
  font-size: 12px;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.message {
  margin: 8px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.primary {
  padding: 8px 14px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
}
</style>
