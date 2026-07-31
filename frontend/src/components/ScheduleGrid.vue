<script setup lang="ts">
import { computed } from 'vue'
import { SLOT_COUNT } from '@/constants'
import type { Member, Schedule } from '@/types'
import {
  buildBlocks,
  buildColumns,
  buildDayHeaders,
  rowForSlot,
  totalColumns,
} from '@/utils/gridLayout'
import { describeSchedule, slotToTime } from '@/utils/timeSlot'

const props = defineProps<{ members: Member[]; schedules: Schedule[] }>()
const emit = defineEmits<{ select: [schedule: Schedule] }>()

const columns = computed(() => buildColumns(props.members))
const dayHeaders = computed(() => buildDayHeaders(props.members.length))
const blocks = computed(() => buildBlocks(props.members, props.schedules))
const slots = computed(() => Array.from({ length: SLOT_COUNT }, (_, i) => i))

const gridStyle = computed(() => ({
  gridTemplateColumns:
    `var(--time-col) repeat(${totalColumns(props.members.length) - 1},` +
    ' minmax(76px, 1fr))',
  gridTemplateRows: `28px 26px repeat(${SLOT_COUNT}, var(--slot-height))`,
}))

const bodyRows = computed(() => `${rowForSlot(0)} / ${rowForSlot(SLOT_COUNT)}`)

function tooltip(schedule: Schedule): string {
  const when = describeSchedule(
    schedule.day_of_week,
    schedule.start_slot,
    schedule.end_slot,
  )
  return `${when} ${schedule.title}`
}
</script>

<template>
  <p v-if="members.length === 0" class="empty">
    위에서 이름을 선택하면 시간표가 나타납니다.
  </p>

  <div v-else class="scroll">
    <div class="grid" :style="gridStyle">
      <div class="corner" />

      <div
        v-for="head in dayHeaders"
        :key="`day-${head.day}`"
        class="day-head"
        :style="{
          gridColumn: `${head.gridColumnStart} / span ${head.span}`,
          gridRow: 1,
        }"
      >
        {{ head.label }}
      </div>

      <div
        v-for="(column, index) in columns"
        :key="`name-${column.day}-${column.member.id}`"
        class="name-head"
        :class="{ 'day-start': index % members.length === 0 }"
        :style="{ gridColumn: column.gridColumn, gridRow: 2 }"
      >
        {{ column.member.name }}
      </div>

      <div
        v-for="slot in slots"
        :key="`time-${slot}`"
        class="time"
        :class="{ hour: slot % 2 === 0 }"
        :style="{ gridColumn: 1, gridRow: rowForSlot(slot) }"
      >
        {{ slotToTime(slot) }}
      </div>

      <div
        v-for="(column, index) in columns"
        :key="`bg-${column.day}-${column.member.id}`"
        class="column-bg"
        :class="{ 'day-start': index % members.length === 0 }"
        :style="{ gridColumn: column.gridColumn, gridRow: bodyRows }"
      />

      <button
        v-for="block in blocks"
        :key="block.schedule.id"
        type="button"
        class="block"
        :title="tooltip(block.schedule)"
        :style="{
          gridColumn: block.gridColumn,
          gridRow: `${block.gridRowStart} / ${block.gridRowEnd}`,
          backgroundColor: block.schedule.color,
        }"
        @click="emit('select', block.schedule)"
      >
        <span class="block-title">{{ block.schedule.title }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.empty {
  padding: 48px 0;
  text-align: center;
  color: var(--muted);
}

.scroll {
  overflow: auto;
  max-height: calc(100vh - 240px);
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: var(--surface);
}

.grid {
  display: grid;
  min-width: max-content;
}

.corner {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 4;
  grid-column: 1;
  grid-row: 1 / 3;
  background: var(--surface);
  border-right: 1px solid var(--line-strong);
  border-bottom: 1px solid var(--line-strong);
}

.day-head,
.name-head {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  font-size: 12px;
  white-space: nowrap;
}

.day-head {
  position: sticky;
  top: 0;
  z-index: 3;
  font-weight: 700;
  border-bottom: 1px solid var(--line-soft);
  border-left: 2px solid var(--line-strong);
}

.name-head {
  position: sticky;
  top: 28px;
  z-index: 3;
  color: var(--muted);
  border-bottom: 1px solid var(--line-strong);
}

.name-head.day-start,
.column-bg.day-start {
  border-left: 2px solid var(--line-strong);
}

.time {
  position: sticky;
  left: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 6px;
  background: var(--surface);
  border-right: 1px solid var(--line-strong);
  font-size: 10px;
  color: var(--muted);
}

.time.hour {
  color: var(--text);
  font-weight: 600;
}

/* 30분마다 옅은 선, 1시간마다 진한 선. 칸을 하나씩 만들지 않고 배경으로 그린다. */
.column-bg {
  border-right: 1px solid var(--line-soft);
  background-image:
    repeating-linear-gradient(
      to bottom,
      var(--line-strong) 0 1px,
      transparent 1px calc(var(--slot-height) * 2)
    ),
    repeating-linear-gradient(
      to bottom,
      var(--line-soft) 0 1px,
      transparent 1px var(--slot-height)
    );
}

/* 몇 칸을 차지하든 블록은 하나. 제목도 그 안에 한 번만 들어간다. */
.block {
  z-index: 1;
  margin: 1px;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: none;
  border-radius: 4px;
  color: #fff;
  text-shadow: 0 1px 1px rgb(0 0 0 / 25%);
}

.block-title {
  font-size: 12px;
  line-height: 1.25;
  text-align: center;
  overflow: hidden;
  word-break: break-all;
}
</style>
