<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES, PALETTE, SLOT_COUNT, TITLE_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { slotOptions } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ memberId: number; schedule?: Schedule }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const readonly = computed(() => !store.canEdit(props.memberId))

const day = ref(props.schedule?.day_of_week ?? 0)
const start = ref(props.schedule?.start_slot ?? 6)
const end = ref(props.schedule?.end_slot ?? 8)
const title = ref(props.schedule?.title ?? '')
const color = ref<string>(props.schedule?.color ?? PALETTE[0])

const message = ref('')
const busy = ref(false)
const confirmingDelete = ref(false)

const startOptions = computed(() =>
  slotOptions().filter((option) => option.value < SLOT_COUNT),
)
const endOptions = computed(() =>
  slotOptions().filter((option) => option.value > start.value),
)

// 시작을 뒤로 옮기면 종료가 앞서지 않도록 함께 민다.
watch(start, (value) => {
  if (end.value <= value) {
    end.value = value + 1
  }
})

const heading = computed(() => {
  const owner = store.memberById(props.memberId)?.name ?? ''
  if (readonly.value) {
    return `${owner} 님의 일정`
  }
  return props.schedule ? '일정 수정' : '일정 추가'
})

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청에 실패했습니다.'
}

async function submit() {
  if (readonly.value) {
    return
  }
  message.value = ''
  busy.value = true
  const creds = store.credentialsFor(props.memberId)
  try {
    if (props.schedule) {
      await api.updateSchedule(
        props.schedule.id,
        {
          day_of_week: day.value,
          start_slot: start.value,
          end_slot: end.value,
          title: title.value.trim(),
          color: color.value,
        },
        creds,
      )
    } else {
      await api.createSchedule(
        {
          member_id: props.memberId,
          day_of_week: day.value,
          start_slot: start.value,
          end_slot: end.value,
          title: title.value.trim(),
          color: color.value,
        },
        creds,
      )
    }
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!props.schedule) {
    return
  }
  message.value = ''
  busy.value = true
  try {
    await api.deleteSchedule(
      props.schedule.id,
      store.credentialsFor(props.memberId),
    )
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog :title="heading" @close="emit('close')">
    <form @submit.prevent="submit">
      <label>
        요일
        <select v-model.number="day" :disabled="readonly">
          <option v-for="(label, index) in DAY_NAMES" :key="label" :value="index">
            {{ label }}요일
          </option>
        </select>
      </label>

      <div class="row">
        <label>
          시작
          <select v-model.number="start" :disabled="readonly">
            <option
              v-for="option in startOptions"
              :key="`s-${option.value}`"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
        <label>
          종료
          <select v-model.number="end" :disabled="readonly">
            <option
              v-for="option in endOptions"
              :key="`e-${option.value}`"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <label>
        제목
        <input
          v-model="title"
          :maxlength="TITLE_MAX_LEN"
          :disabled="readonly"
          placeholder="전공수업, 알바 …"
          autocomplete="off"
        />
      </label>

      <div class="palette">
        <button
          v-for="swatch in PALETTE"
          :key="swatch"
          type="button"
          class="swatch"
          :class="{ on: color === swatch }"
          :style="{ backgroundColor: swatch }"
          :disabled="readonly"
          :aria-label="`색상 ${swatch}`"
          @click="color = swatch"
        />
      </div>

      <p v-if="message" class="message">{{ message }}</p>

      <div v-if="confirmingDelete" class="confirm">
        <span>이 일정을 지웁니다.</span>
        <button type="button" @click="confirmingDelete = false">아니오</button>
        <button type="button" class="danger" :disabled="busy" @click="remove">
          삭제합니다
        </button>
      </div>

      <div class="actions">
        <button
          v-if="schedule && !readonly && !confirmingDelete"
          type="button"
          class="danger"
          @click="confirmingDelete = true"
        >
          삭제
        </button>
        <span class="spacer" />
        <button type="button" @click="emit('close')">
          {{ readonly ? '닫기' : '취소' }}
        </button>
        <button v-if="!readonly" type="submit" class="primary" :disabled="busy">
          저장
        </button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 12px;
}

.row label {
  flex: 1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}

input,
select {
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text);
}

.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.swatch {
  width: 28px;
  height: 28px;
  border: 2px solid transparent;
  border-radius: 6px;
}

.swatch.on {
  border-color: var(--text);
}

.message {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #fef3c7;
  font-size: 13px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spacer {
  flex: 1;
}

.actions button,
.confirm button {
  padding: 8px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
}

.primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: #fff;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.confirm .danger {
  background: #dc2626 !important;
  color: #fff;
}
</style>
