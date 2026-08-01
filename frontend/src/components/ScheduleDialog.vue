<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ApiError, api } from '@/api/client'
import { DAY_NAMES, PALETTE, SLOT_COUNT, TITLE_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Schedule } from '@/types'
import { textOn } from '@/utils/contrast'
import { slotOptions } from '@/utils/timeSlot'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{
  memberId: number
  schedule?: Schedule
  /** 격자를 끌어서 만든 자리. 요일과 시간이 미리 채워진다. */
  preset?: { day: number; start: number; end: number }
}>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const readonly = computed(() => !store.canEdit(props.memberId))

const day = ref(props.schedule?.day_of_week ?? props.preset?.day ?? 0)
const start = ref(props.schedule?.start_slot ?? props.preset?.start ?? 6)
const end = ref(props.schedule?.end_slot ?? props.preset?.end ?? 8)
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
  message.value = err instanceof ApiError ? err.message : '요청이 실패했습니다.'
}

async function submit() {
  if (readonly.value) {
    return
  }
  message.value = ''
  busy.value = true
  const creds = store.credentialsFor(props.memberId)
  const fields = {
    day_of_week: day.value,
    start_slot: start.value,
    end_slot: end.value,
    title: title.value.trim(),
    color: color.value,
  }
  try {
    if (props.schedule) {
      await api.updateSchedule(props.schedule.id, fields, creds)
    } else {
      await api.createSchedule({ member_id: props.memberId, ...fields }, creds)
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
    <form class="stack" @submit.prevent="submit">
      <label class="field">
        <span>요일</span>
        <select v-model.number="day" class="select" :disabled="readonly">
          <option v-for="(label, index) in DAY_NAMES" :key="label" :value="index">
            {{ label }}요일
          </option>
        </select>
      </label>

      <div class="field-row">
        <label class="field">
          <span>시작</span>
          <select v-model.number="start" class="select" :disabled="readonly">
            <option
              v-for="option in startOptions"
              :key="`s-${option.value}`"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>종료</span>
          <select v-model.number="end" class="select" :disabled="readonly">
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

      <label class="field">
        <span>제목</span>
        <input
          v-model="title"
          class="input"
          :maxlength="TITLE_MAX_LEN"
          :disabled="readonly"
          placeholder="전공수업, 알바 …"
          autocomplete="off"
        />
      </label>

      <div class="field">
        <span>색</span>
        <div class="swatches">
          <button
            v-for="option in PALETTE"
            :key="option"
            type="button"
            class="swatch"
            :class="{ on: color === option }"
            :style="{ backgroundColor: option, color: textOn(option) }"
            :disabled="readonly"
            :aria-label="`색 ${option}`"
            :aria-pressed="color === option"
            @click="color = option"
          />
        </div>
      </div>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <p v-if="confirmingDelete" class="notice notice--warn confirm">
        <span>이 일정을 지웁니다.</span>
        <button
          type="button"
          class="btn btn--sm"
          @click="confirmingDelete = false"
        >
          그만두기
        </button>
        <button
          type="button"
          class="btn btn--sm btn--fill-danger"
          :disabled="busy"
          @click="remove"
        >
          지웁니다
        </button>
      </p>

      <div class="row-end">
        <button
          v-if="schedule && !readonly && !confirmingDelete"
          type="button"
          class="btn btn--danger"
          @click="confirmingDelete = true"
        >
          삭제
        </button>
        <span class="spacer" />
        <button type="button" class="btn" @click="emit('close')">
          {{ readonly ? '닫기' : '취소' }}
        </button>
        <button
          v-if="!readonly"
          type="submit"
          class="btn btn--primary"
          :disabled="busy"
        >
          저장
        </button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

/* 고른 색에만 체크가 드러난다. 테두리로 표시하면 밝은 색에서 잘 안 보인다. */
.swatch {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.82;
  transition: opacity 110ms ease, transform 110ms ease;
}

.swatch:hover {
  opacity: 1;
}

.swatch.on {
  opacity: 1;
  transform: scale(1.06);
}

.swatch.on::after {
  content: "✓";
  font-weight: 700;
}

.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.confirm > span {
  flex: 1 1 100%;
}
</style>
