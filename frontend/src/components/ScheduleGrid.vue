<script setup lang="ts">
import { computed } from 'vue'
import { SLOT_COUNT } from '@/constants'
import type { Member, Schedule } from '@/types'
import { textOn } from '@/utils/contrast'
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
    `var(--ruler-w) repeat(${totalColumns(props.members.length) - 1},` +
    ' minmax(var(--col-min), 1fr))',
  gridTemplateRows: `30px 24px repeat(${SLOT_COUNT}, var(--slot-h))`,
}))

const bodyRows = computed(() => `${rowForSlot(0)} / ${rowForSlot(SLOT_COUNT)}`)

/** 정각 눈금에만 숫자를 새긴다. 슬롯 0은 06, 34는 23. */
function hourMark(slot: number): string {
  return String(6 + slot / 2).padStart(2, '0')
}

function tooltip(schedule: Schedule): string {
  const when = describeSchedule(
    schedule.day_of_week,
    schedule.start_slot,
    schedule.end_slot,
  )
  return `${when} · ${schedule.title}`
}

function span(schedule: Schedule): string {
  return `${slotToTime(schedule.start_slot)}–${slotToTime(schedule.end_slot)}`
}
</script>

<template>
  <p v-if="members.length === 0" class="empty">
    왼쪽에서 이름을 고르면 시간표가 나타납니다.
  </p>

  <div v-else class="sheet">
    <div class="grid" :style="gridStyle">
      <div class="corner" />

      <div
        v-for="head in dayHeaders"
        :key="`day-${head.day}`"
        class="day"
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
        class="who"
        :class="{ 'day-start': index % members.length === 0 }"
        :style="{ gridColumn: column.gridColumn, gridRow: 2 }"
      >
        {{ column.member.name }}
      </div>

      <!-- 시간은 칸이 아니라 축이다. 격자 대신 눈금으로 새긴다. -->
      <div
        v-for="slot in slots"
        :key="`tick-${slot}`"
        class="tick"
        :class="{ hour: slot % 2 === 0 }"
        :style="{ gridColumn: 1, gridRow: rowForSlot(slot) }"
      >
        <span v-if="slot % 2 === 0">{{ hourMark(slot) }}</span>
      </div>

      <div
        v-for="(column, index) in columns"
        :key="`lane-${column.day}-${column.member.id}`"
        class="lane"
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
          color: textOn(block.schedule.color),
        }"
        @click="emit('select', block.schedule)"
      >
        <span class="title">{{ block.schedule.title }}</span>
        <span
          v-if="block.gridRowEnd - block.gridRowStart >= 3"
          class="span"
        >
          {{ span(block.schedule) }}
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.empty {
  padding: 72px 0;
  text-align: center;
  color: var(--mute);
}

.sheet {
  overflow: auto;
  max-height: calc(100vh - 118px);
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: 6px;
}

/*
 * min-width: max-content 를 쓰면 가장 긴 일정 제목이 열 너비를 정해 버린다.
 * 열은 --col-min 으로 고정하고, 제목은 그 안에서 줄바꿈시킨다.
 */
.grid {
  display: grid;
}

.corner {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 4;
  grid-column: 1;
  grid-row: 1 / 3;
  background: var(--paper);
  border-bottom: 1px solid var(--ink);
}

.day,
.who {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper);
  white-space: nowrap;
}

.day {
  position: sticky;
  top: 0;
  z-index: 3;
  font-size: 14px;
  font-weight: 700;
  border-left: 1px solid var(--rule-strong);
}

.who {
  position: sticky;
  top: 30px;
  z-index: 3;
  font-size: 11px;
  color: var(--mute);
  border-bottom: 1px solid var(--ink);
  border-left: 1px solid rgb(23 24 28 / 6%);
}

.who.day-start {
  border-left: 1px solid var(--rule-strong);
}

/* 눈금자: 정각은 긴 눈금과 숫자, 30분은 짧은 눈금. */
.tick {
  position: sticky;
  left: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 19px;
  background: var(--paper);
  font-family: var(--mono);
  font-size: 10.5px;
  font-variant-numeric: tabular-nums;
  color: var(--mute);
}

/* 눈금은 셀 위쪽 경계에 놓여 정각 가로줄과 같은 높이에서 만난다. */
.tick::after {
  content: "";
  position: absolute;
  right: 0;
  top: 0;
  width: 7px;
  border-top: 1px solid var(--rule-strong);
}

.tick.hour {
  color: var(--ink);
  font-weight: 600;
}

.tick.hour::after {
  width: 15px;
  border-top-color: var(--ink);
}

/* 가로줄은 정각에만. 30분 줄무늬는 눈금자에 넘겼다. */
.lane {
  border-left: 1px solid rgb(23 24 28 / 6%);
  background-image: repeating-linear-gradient(
    to bottom,
    var(--rule) 0 1px,
    transparent 1px calc(var(--slot-h) * 2)
  );
}

.lane.day-start {
  border-left: 1px solid var(--rule-strong);
}

/*
 * 몇 칸을 차지하든 블록은 하나. 제목은 그 안에 한 번만 들어가고,
 * 시작 시각과 붙어 보이도록 위쪽에 정렬한다.
 */
.block {
  z-index: 1;
  margin: 0 2px 1px 1px;
  padding: 3px 6px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  overflow: hidden;
  border: none;
  border-radius: 4px;
  box-shadow: inset 0 0 0 1px rgb(23 24 28 / 10%);
  text-align: left;
  transition: filter 120ms ease;
}

/* 파스텔은 밝히면 배경에 묻힌다. 눌러 주는 쪽이 눈에 띈다. */
.block:hover {
  filter: brightness(0.955);
}

.title {
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
  word-break: break-all;
}

/* 세 칸(1시간 30분) 이상이면 시각까지 들어갈 자리가 생긴다. */
.span {
  font-family: var(--mono);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}
@media (max-width: 860px) {
  /* 사이드바가 위로 올라오므로 격자에 화면 전부를 주지 않는다. */
  .sheet {
    max-height: 62vh;
  }

  /* 좁은 열에서는 시각이 두 줄로 접힌다. 제목만 남긴다. */
  .span {
    display: none;
  }
}
</style>
