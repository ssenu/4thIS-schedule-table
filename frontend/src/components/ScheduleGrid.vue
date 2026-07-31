<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { MIN_COLUMN_WIDTH, RULER_WIDTH, SLOT_COUNT } from '@/constants'
import type { Member, Schedule } from '@/types'
import { textOn } from '@/utils/contrast'
import { daysPerPage, pageLabel, splitIntoPages } from '@/utils/dayPages'
import {
  buildBlocks,
  buildColumns,
  buildDayHeaders,
  rowForSlot,
  totalColumns,
} from '@/utils/gridLayout'
import { describeSchedule, slotToTime } from '@/utils/timeSlot'

const props = defineProps<{
  members: Member[]
  schedules: Schedule[]
  /** 다이얼로그가 열려 있을 때 방향키를 가로채지 않는다. */
  paused?: boolean
}>()
const emit = defineEmits<{ select: [schedule: Schedule] }>()

const frame = ref<HTMLElement>()
const width = ref(0)
const pageIndex = ref(0)

/* ── 요일 페이지 ─────────────────────────────────────────────── */

const pages = computed(() =>
  splitIntoPages(
    daysPerPage(
      Math.max(0, width.value - RULER_WIDTH),
      props.members.length,
      MIN_COLUMN_WIDTH,
    ),
  ),
)

const currentDays = computed(() => pages.value[pageIndex.value] ?? [])

// 인원이나 창 크기가 바뀌면 페이지 수가 달라진다. 넘어간 자리는 끝으로 당긴다.
watch(pages, (list) => {
  if (pageIndex.value > list.length - 1) {
    pageIndex.value = Math.max(0, list.length - 1)
  }
})

function go(step: number) {
  const next = pageIndex.value + step
  if (next >= 0 && next < pages.value.length) {
    pageIndex.value = next
  }
}

/* ── 잡아끌어 넘기기 ─────────────────────────────────────────── */

/** 이만큼 끌면 페이지가 넘어간다. */
const SNAP = 56
/** 이보다 조금 움직였으면 넘기려던 게 아니라 누른 것으로 본다. */
const CLICK_SLOP = 8

const dragOffset = ref(0)
const dragging = ref(false)
let startX = 0
let activePointer: number | null = null
let suppressClick = false

function onPointerDown(event: PointerEvent) {
  if (pages.value.length < 2 || event.button !== 0) {
    return
  }
  activePointer = event.pointerId
  startX = event.clientX
  dragging.value = true
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (activePointer !== event.pointerId) {
    return
  }
  const dx = event.clientX - startX
  // 끝 페이지에서는 저항을 키워 더 갈 곳이 없다는 걸 손으로 알린다.
  const atEdge =
    (dx > 0 && pageIndex.value === 0) ||
    (dx < 0 && pageIndex.value === pages.value.length - 1)
  dragOffset.value = dx * (atEdge ? 0.16 : 0.4)
}

function onPointerUp(event: PointerEvent) {
  if (activePointer !== event.pointerId) {
    return
  }
  const dx = event.clientX - startX
  if (Math.abs(dx) >= SNAP) {
    go(dx < 0 ? 1 : -1)
  }
  suppressClick = Math.abs(dx) >= CLICK_SLOP
  dragOffset.value = 0
  dragging.value = false
  activePointer = null
}

/** 끌고 나서 손을 뗀 자리의 블록이 열리면 안 된다. */
function onBlockClick(schedule: Schedule) {
  if (suppressClick) {
    suppressClick = false
    return
  }
  emit('select', schedule)
}

/* ── 키보드 ──────────────────────────────────────────────────── */

function onKey(event: KeyboardEvent) {
  if (props.paused || pages.value.length < 2) {
    return
  }
  const tag = (document.activeElement?.tagName ?? '').toLowerCase()
  if (tag === 'input' || tag === 'select' || tag === 'textarea') {
    return
  }
  if (event.key === 'ArrowRight') {
    go(1)
    event.preventDefault()
  } else if (event.key === 'ArrowLeft') {
    go(-1)
    event.preventDefault()
  }
}

let observer: ResizeObserver | undefined

onMounted(() => {
  window.addEventListener('keydown', onKey)
  if (frame.value) {
    observer = new ResizeObserver(([entry]) => {
      width.value = entry.contentRect.width
    })
    observer.observe(frame.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  observer?.disconnect()
})

/* ── 그리기 ──────────────────────────────────────────────────── */

const columns = computed(() => buildColumns(props.members, currentDays.value))
const dayHeaders = computed(() =>
  buildDayHeaders(props.members.length, currentDays.value),
)
const blocks = computed(() =>
  buildBlocks(props.members, props.schedules, currentDays.value),
)

/** 정각마다 한 줄. 06:00 자리는 이름 헤더의 아래 선이 대신한다. */
const hourSlots = computed(() =>
  Array.from({ length: SLOT_COUNT }, (_, slot) => slot).filter(
    (slot) => slot > 0 && slot % 2 === 0,
  ),
)

const gridStyle = computed(() => ({
  gridTemplateColumns:
    `var(--ruler-w) repeat(` +
    `${totalColumns(props.members.length, currentDays.value.length) - 1}, 1fr)`,
  gridTemplateRows: `30px 24px repeat(${SLOT_COUNT}, minmax(0, 1fr))`,
  transform: dragOffset.value ? `translateX(${dragOffset.value}px)` : '',
  transition: dragging.value ? 'none' : 'transform 160ms ease',
}))

const bodyRows = computed(() => `${rowForSlot(0)} / ${rowForSlot(SLOT_COUNT)}`)

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
  <div ref="frame" class="frame">
    <p v-if="members.length === 0" class="empty">
      왼쪽에서 이름을 고르면 시간표가 나타납니다.
    </p>

    <template v-else>
      <div
        class="sheet"
        :class="{ pageable: pages.length > 1, dragging }"
        tabindex="0"
        role="group"
        :aria-label="
          pages.length > 1
            ? '시간표. 좌우 방향키로 요일을 넘깁니다.'
            : '시간표'
        "
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
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
            v-for="slot in SLOT_COUNT"
            :key="`tick-${slot - 1}`"
            class="tick"
            :class="{ hour: (slot - 1) % 2 === 0 }"
            :style="{ gridColumn: 1, gridRow: rowForSlot(slot - 1) }"
          >
            <span v-if="(slot - 1) % 2 === 0">{{ hourMark(slot - 1) }}</span>
          </div>

          <div
            v-for="(column, index) in columns"
            :key="`lane-${column.day}-${column.member.id}`"
            class="lane"
            :class="{ 'day-start': index % members.length === 0 }"
            :style="{ gridColumn: column.gridColumn, gridRow: bodyRows }"
          />

          <!-- 가로줄은 정각에만. 행 높이가 화면에 따라 변해도 자리가 맞는다. -->
          <div
            v-for="slot in hourSlots"
            :key="`hour-${slot}`"
            class="hour-line"
            :style="{ gridColumn: '2 / -1', gridRow: rowForSlot(slot) }"
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
            @click="onBlockClick(block.schedule)"
          >
            <span class="title">{{ block.schedule.title }}</span>
            <span v-if="block.gridRowEnd - block.gridRowStart >= 3" class="span">
              {{ span(block.schedule) }}
            </span>
          </button>
        </div>
      </div>

      <div v-if="pages.length > 1" class="pager">
        <button
          type="button"
          class="btn btn--sm"
          :disabled="pageIndex === 0"
          aria-label="이전 요일"
          @click="go(-1)"
        >
          ←
        </button>
        <span class="range">{{ pageLabel(currentDays) }}</span>
        <span class="dots" aria-hidden="true">
          <i
            v-for="index in pages.length"
            :key="`dot-${index}`"
            :class="{ on: index - 1 === pageIndex }"
          />
        </span>
        <button
          type="button"
          class="btn btn--sm"
          :disabled="pageIndex === pages.length - 1"
          aria-label="다음 요일"
          @click="go(1)"
        >
          →
        </button>
        <span class="tip">끌거나 ← → 키로 넘깁니다</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 화면 높이에 맞춰 하루치가 통째로 들어간다. 세로 스크롤은 두지 않는다. */
.frame {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 104px);
}

.empty {
  padding: 72px 0;
  text-align: center;
  color: var(--mute);
}

.sheet {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: 6px;
  touch-action: pan-y;
}

.sheet.pageable {
  cursor: grab;
}

.sheet.dragging {
  cursor: grabbing;
  user-select: none;
}

.grid {
  display: grid;
  height: 100%;
}

.corner {
  z-index: 2;
  grid-column: 1;
  grid-row: 1 / 3;
  background: var(--paper);
  border-bottom: 1px solid var(--ink);
}

.day,
.who {
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper);
  white-space: nowrap;
  overflow: hidden;
}

.day {
  font-size: 14px;
  font-weight: 700;
  border-left: 1px solid var(--rule-strong);
}

.who {
  font-size: 11px;
  color: var(--mute);
  border-bottom: 1px solid var(--ink);
  border-left: 1px solid rgb(23 24 28 / 6%);
  text-overflow: ellipsis;
}

.who.day-start {
  border-left: 1px solid var(--rule-strong);
}

/* 눈금자: 정각은 긴 눈금과 숫자, 30분은 짧은 눈금. */
.tick {
  position: relative;
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

.lane {
  border-left: 1px solid rgb(23 24 28 / 6%);
}

.lane.day-start {
  border-left: 1px solid var(--rule-strong);
}

.hour-line {
  border-top: 1px solid var(--rule);
  pointer-events: none;
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

.span {
  font-family: var(--mono);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}

/* ── 페이지 표시 ─────────────────────────────────────────────── */

.pager {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 9px;
}

.range {
  font-weight: 700;
  letter-spacing: 0.02em;
}

.dots {
  display: flex;
  gap: 5px;
}

.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--rule-strong);
  transition: background 140ms ease;
}

.dots i.on {
  background: var(--ink);
}

.tip {
  margin-left: auto;
  font-size: 11px;
  color: var(--mute);
}

@media (max-width: 860px) {
  /*
   * 좁은 화면에서 서른여섯 줄을 다 욱여넣으면 한 줄이 8px 남짓이라 읽을 수 없다.
   * 여기서는 줄 높이를 지키고 세로로 스크롤한다.
   */
  .frame {
    height: auto;
  }

  .sheet {
    overflow: auto;
    max-height: 62vh;
  }

  .grid {
    height: 780px;
  }

  .span {
    display: none;
  }

  .tip {
    display: none;
  }
}
</style>
