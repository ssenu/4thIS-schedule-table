<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { slotToTime } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ memberId: number }>()
const emit = defineEmits<{
  close: []
  create: [memberId: number]
  edit: [schedule: Schedule]
}>()

const store = useBoardStore()
const rows = computed(() => store.schedulesOf(props.memberId))
const owner = computed(() => store.memberById(props.memberId)?.name ?? '')

const pendingDelete = ref<number | null>(null)
const message = ref('')
const busy = ref(false)

async function remove(schedule: Schedule) {
  message.value = ''
  busy.value = true
  try {
    await api.deleteSchedule(schedule.id, store.credentialsFor(props.memberId))
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
  <BaseDialog :title="`${owner} 일정`" wide @close="emit('close')">
    <p v-if="rows.length === 0" class="notice notice--quiet">
      아직 넣은 일정이 없습니다. 격자를 끌어서 만들거나 아래 버튼을 누르세요.
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
        type="button"
        class="btn btn--primary"
        @click="emit('create', memberId)"
      >
        일정 추가
      </button>
    </div>
  </BaseDialog>
</template>

<style scoped>
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
