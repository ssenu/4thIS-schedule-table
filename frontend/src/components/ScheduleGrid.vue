<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { MIN_COLUMN_WIDTH, RULER_WIDTH, SLOT_COUNT } from '@/constants'
import type { Member, Schedule } from '@/types'
import type { ColorMode } from '@/utils/blockColor'
import { blockColor } from '@/utils/blockColor'
import { textOn } from '@/utils/contrast'
import type { DraftBox } from '@/utils/draftBox'
import {
  clashes,
  fromDrag,
  moveTo,
  resizeEnd,
  resizeStart,
} from '@/utils/draftBox'
import { daysPerPage, pageLabel, splitIntoPages } from '@/utils/dayPages'
import type { GridColumn } from '@/utils/gridLayout'
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
  /** 수정 중인 사람. 이 사람 열에서는 끌어서 일정을 만든다. */
  editingMemberId?: number | null
  /** 블록 색을 무엇으로 정할지. */
  colorMode?: ColorMode
}>()
interface Placement {
  schedule: Schedule
  day: number
  start: number
  end: number
}

const emit = defineEmits<{
  select: [schedule: Schedule]
  draft: [value: { memberId: number; day: number; start: number; end: number }]
  /** 있던 일정을 다른 자리로 옮겼다. */
  move: [value: Placement]
  /** Ctrl 을 누른 채 옮겨 원본을 두고 하나 더 만든다. */
  copy: [value: Placement]
  /** 겹치는 자리에 놓으려 했다. */
  clash: []
}>()

const editing = computed(
  () => props.editingMemberId !== null && props.editingMemberId !== undefined,
)

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

/** 포인터를 요소에 묶어 밖으로 나가도 따라오게 한다. 실패해도 진행에 지장은 없다. */
function capture(event: PointerEvent) {
  try {
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  } catch {
    // 활성 포인터가 아니면 무시한다.
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
  // 수정 중에는 끄는 동작이 일정 만들기다. 페이지는 화살표와 방향키로 넘긴다.
  if (editing.value || pages.value.length < 2 || event.button !== 0) {
    return
  }
  activePointer = event.pointerId
  startX = event.clientX
  dragging.value = true
  capture(event)
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
  // 초안을 물린다. 다이얼로그가 열려 있으면 ESC 는 그쪽 몫이다.
  if (event.key === 'Escape' && !props.paused && draft.value !== null) {
    clearDraft()
    event.preventDefault()
    return
  }
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

/* ── 수정 중: 끌어서 일정 만들기 ─────────────────────────────── */

/**
 * 초안을 지금 무엇으로 만지고 있는지. null 이면 그냥 놓여 있는 상태다.
 *
 * 놓여 있는 동안 ⊕ 가 뜨고, 그걸 눌러야 폼이 열린다. 손을 뗐다고 바로
 * 폼이 뜨면 시간을 잘못 잡았을 때 처음부터 다시 끌어야 한다.
 */
type DraftMode = 'drawing' | 'resize-start' | 'resize-end' | 'moving'

const draft = ref<DraftBox | null>(null)
const draftEl = ref<HTMLElement>()
let draftPointer: number | null = null
const draftMode = ref<DraftMode | null>(null)
/** 처음 그릴 때 누른 칸. 위로 끌든 아래로 끌든 여기서 잰다. */
let drawAnchor = 0
/** 옮길 때 블록 위 끝에서 몇 칸 아래를 잡았는지. */
let moveGrab = 0
/** 누르기만 하고 뗀 것인지 알려면, 누를 때 초안이 있었는지 기억해야 한다. */
let hadDraft = false

/** 지금 잡아 옮기고 있는 기존 일정. 새로 그리는 초안과는 다르다. */
const moving = ref<Schedule | null>(null)
/** 옮기는 동안 Ctrl(맥은 Cmd)을 누르고 있으면 원본을 두고 하나 더 만든다. */
const copying = ref(false)
/** 제자리에서 뗐으면 옮긴 게 아니라 누른 것이다. */
let blockMoved = false

/**
 * 지금 자리가 이미 있는 일정과 부딪히는지.
 *
 * 옮기는 중이라면 자기 자신은 빼고 본다 — 제 자리와 겹쳤다고 할 수는 없다.
 * 복사할 때는 원본도 남으므로 자신까지 센다.
 */
const draftClash = computed(() => {
  const box = draft.value
  if (box === null || props.editingMemberId == null) {
    return false
  }
  const self = moving.value !== null && !copying.value ? moving.value.id : undefined
  return clashes(box, props.schedules, props.editingMemberId, self)
})

/** 열 안에서의 세로 위치를 슬롯 번호로. 줄 높이가 화면마다 달라 비율로 잰다. */
function slotAt(element: HTMLElement, clientY: number): number {
  const rect = element.getBoundingClientRect()
  const ratio = (clientY - rect.top) / rect.height
  return Math.max(0, Math.min(SLOT_COUNT - 1, Math.floor(ratio * SLOT_COUNT)))
}

/** 수정 중인 본인 열에서만 새 일정을 그릴 수 있다. */
function canDraw(column: GridColumn): boolean {
  return editing.value && column.member.id === props.editingMemberId
}

/**
 * 좌표 아래에 있는 본인 열을 찾는다.
 *
 * 포인터를 붙잡아 둔 동안에는 event.currentTarget 이 처음 누른 열에 묶여
 * 바뀌지 않는다. 요일을 넘나들려면 좌표로 다시 찾는 수밖에 없다.
 */
function laneAt(x: number, y: number): { day: number; el: HTMLElement } | null {
  for (const el of document.elementsFromPoint(x, y)) {
    if (!(el instanceof HTMLElement) || el.dataset.lane === undefined) {
      continue
    }
    // 남의 열 위로는 옮길 수 없다. 본인 열에서만 그린다는 규칙 그대로다.
    if (Number(el.dataset.member) !== props.editingMemberId) {
      return null
    }
    return { day: Number(el.dataset.day), el }
  }
  return null
}

function clearDraft() {
  draft.value = null
  draftMode.value = null
  draftPointer = null
  moving.value = null
  copying.value = false
}

/* 빈 칸에서 새로 그리기 */

function onLaneDown(event: PointerEvent, column: GridColumn) {
  if (!canDraw(column) || event.button !== 0) {
    return
  }
  hadDraft = draft.value !== null
  drawAnchor = slotAt(event.currentTarget as HTMLElement, event.clientY)
  draft.value = fromDrag(column.day, drawAnchor, drawAnchor)
  draftMode.value = 'drawing'
  draftPointer = event.pointerId
  capture(event)
  event.preventDefault()
}

function onLaneMove(event: PointerEvent) {
  if (draftPointer !== event.pointerId || draftMode.value !== 'drawing') {
    return
  }
  const slot = slotAt(event.currentTarget as HTMLElement, event.clientY)
  draft.value = fromDrag(draft.value!.day, drawAnchor, slot)
}

function onLaneUp(event: PointerEvent) {
  if (draftPointer !== event.pointerId || draftMode.value !== 'drawing') {
    return
  }
  // 이미 초안이 있는데 끌지 않고 누르기만 했다면 치우라는 뜻이다.
  const stillOneSlot = draft.value!.end - draft.value!.start === 1
  if (hadDraft && stillOneSlot) {
    clearDraft()
    return
  }
  draftMode.value = null
  draftPointer = null
}

/* 놓인 초안을 잡고 고치기 */

function beginGrab(event: PointerEvent, mode: DraftMode) {
  if (draft.value === null || event.button !== 0) {
    return
  }
  draftMode.value = mode
  draftPointer = event.pointerId
  if (mode === 'moving') {
    const lane = laneAt(event.clientX, event.clientY)
    moveGrab = lane === null ? 0 : slotAt(lane.el, event.clientY) - draft.value.start
  }
  // 가장자리에서 시작해도 초안 본체가 포인터를 붙잡게 해서, 이어지는
  // 이동과 뗌을 한 곳에서 받는다.
  try {
    draftEl.value?.setPointerCapture(event.pointerId)
  } catch {
    // 활성 포인터가 아니면 무시한다.
  }
  event.preventDefault()
}

function onDraftMove(event: PointerEvent) {
  if (draftPointer !== event.pointerId || draft.value === null) {
    return
  }
  if (draftMode.value === null || draftMode.value === 'drawing') {
    return
  }
  const lane = laneAt(event.clientX, event.clientY)
  if (lane === null) {
    return
  }
  const slot = slotAt(lane.el, event.clientY)
  if (draftMode.value === 'resize-start') {
    draft.value = resizeStart(draft.value, slot)
  } else if (draftMode.value === 'resize-end') {
    draft.value = resizeEnd(draft.value, slot)
  } else {
    draft.value = moveTo(draft.value, lane.day, slot - moveGrab)
  }
}

function endGrab(event: PointerEvent) {
  if (draftPointer !== event.pointerId) {
    return
  }
  draftMode.value = null
  draftPointer = null
}

/* 있던 일정을 잡아 옮기기 */

/** 수정 중인 본인 일정만 잡을 수 있다. */
function canGrab(schedule: Schedule): boolean {
  return editing.value && schedule.member_id === props.editingMemberId
}

function onBlockDown(event: PointerEvent, schedule: Schedule) {
  if (!canGrab(schedule) || event.button !== 0) {
    return
  }
  // 뗄 때 여기서 직접 판단한다. 뒤따라 오는 click 은 무시한다.
  suppressClick = true
  moving.value = schedule
  copying.value = event.ctrlKey || event.metaKey
  blockMoved = false
  draft.value = {
    day: schedule.day_of_week,
    start: schedule.start_slot,
    end: schedule.end_slot,
  }
  draftMode.value = 'moving'
  draftPointer = event.pointerId
  const lane = laneAt(event.clientX, event.clientY)
  moveGrab =
    lane === null ? 0 : slotAt(lane.el, event.clientY) - schedule.start_slot
  capture(event)
  event.preventDefault()
}

function onBlockMove(event: PointerEvent) {
  if (draftPointer !== event.pointerId || moving.value === null) {
    return
  }
  // 끄는 도중에 마음을 바꿔도 되도록 뗄 때까지 계속 본다.
  copying.value = event.ctrlKey || event.metaKey
  const lane = laneAt(event.clientX, event.clientY)
  if (lane === null || draft.value === null) {
    return
  }
  const next = moveTo(
    draft.value,
    lane.day,
    slotAt(lane.el, event.clientY) - moveGrab,
  )
  if (next.day !== draft.value.day || next.start !== draft.value.start) {
    blockMoved = true
  }
  draft.value = next
}

function onBlockUp(event: PointerEvent) {
  if (draftPointer !== event.pointerId || moving.value === null) {
    return
  }
  const schedule = moving.value
  const box = draft.value
  const copy = copying.value
  const moved = blockMoved
  // 치우고 나면 판정을 다시 할 수 없으니 먼저 읽어 둔다.
  const bumped = draftClash.value
  clearDraft()

  if (!moved || box === null) {
    // 제자리에서 뗐다. 옮긴 게 아니라 누른 것이니 폼을 연다.
    emit('select', schedule)
    return
  }
  if (bumped) {
    emit('clash')
    return
  }
  const placed = { schedule, day: box.day, start: box.start, end: box.end }
  if (copy) {
    emit('copy', placed)
  } else {
    emit('move', placed)
  }
}

/** ⊕. 여기서 비로소 폼이 열린다. */
function openDraftForm() {
  if (draft.value === null || props.editingMemberId == null) {
    return
  }
  const { day, start, end } = draft.value
  emit('draft', { memberId: props.editingMemberId, day, start, end })
  clearDraft()
}

/** 초안이 놓인 열. 요일을 옮기면 따라 바뀐다. */
const draftColumn = computed(() => {
  const box = draft.value
  if (box === null) {
    return null
  }
  const column = columns.value.find(
    (c) => c.day === box.day && c.member.id === props.editingMemberId,
  )
  return column?.gridColumn ?? null
})

/** 맨 오른쪽 열이면 ⊕ 를 왼쪽에 둔다. 그대로 두면 화면 밖으로 밀린다. */
const draftAtEdge = computed(
  () =>
    draftColumn.value !== null &&
    draftColumn.value >=
      totalColumns(props.members.length, currentDays.value.length),
)

/** 수정 모드를 나가면 초안도 걷는다. */
watch(() => props.editingMemberId, clearDraft)

/* ── 그리기 ──────────────────────────────────────────────────── */

/** 화면에 놓인 순서. 인원별 색은 이 자리로 팔레트를 고른다. */
const memberIndex = computed(
  () => new Map(props.members.map((member, index) => [member.id, index])),
)

function paint(schedule: Schedule): string {
  return blockColor(schedule, props.colorMode ?? 'own', memberIndex.value)
}

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
            :class="{
              'day-start': index % members.length === 0,
              editing: column.member.id === editingMemberId,
            }"
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
            :class="{
              'day-start': index % members.length === 0,
              drawable: canDraw(column),
            }"
            data-lane=""
            :data-day="column.day"
            :data-member="column.member.id"
            :style="{ gridColumn: column.gridColumn, gridRow: bodyRows }"
            @pointerdown="onLaneDown($event, column)"
            @pointermove="onLaneMove"
            @pointerup="onLaneUp"
            @pointercancel="onLaneUp"
          />

          <!-- 가로줄은 정각에만. 행 높이가 화면에 따라 변해도 자리가 맞는다. -->
          <div
            v-for="slot in hourSlots"
            :key="`hour-${slot}`"
            class="hour-line"
            :style="{ gridColumn: '2 / -1', gridRow: rowForSlot(slot) }"
          />

          <div
            v-if="draft && draftColumn !== null"
            ref="draftEl"
            class="draft"
            :class="{ held: draftMode !== null, clash: draftClash, copying }"
            :style="{
              gridColumn: draftColumn,
              gridRow: `${rowForSlot(draft.start)} / ${rowForSlot(draft.end)}`,
            }"
            @pointerdown="beginGrab($event, 'moving')"
            @pointermove="onDraftMove"
            @pointerup="endGrab"
            @pointercancel="endGrab"
          >
            <span class="draft-time">
              {{ slotToTime(draft.start) }}–{{ slotToTime(draft.end) }}
              <template v-if="copying && moving">· 복사</template>
            </span>

            <!-- 위아래 끝은 길이를 고치는 손잡이다. 가운데를 잡으면 옮겨진다. -->
            <span
              class="draft-edge draft-edge--top"
              @pointerdown.stop="beginGrab($event, 'resize-start')"
            />
            <span
              class="draft-edge draft-edge--bottom"
              @pointerdown.stop="beginGrab($event, 'resize-end')"
            />

            <button
              v-if="draftMode === null"
              type="button"
              class="draft-add"
              :class="{ 'draft-add--flip': draftAtEdge }"
              :disabled="draftClash"
              :title="
                draftClash
                  ? '이미 있는 일정과 겹칩니다'
                  : '이 시간으로 일정 만들기'
              "
              :aria-label="
                draftClash
                  ? '겹쳐서 일정을 만들 수 없습니다'
                  : '이 시간으로 일정 만들기'
              "
              @pointerdown.stop
              @click="openDraftForm"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 5.5v13M5.5 12h13" />
              </svg>
            </button>
          </div>

          <button
            v-for="block in blocks"
            :key="block.schedule.id"
            type="button"
            class="block"
            :class="{
              grabbable: canGrab(block.schedule),
              ghost: moving?.id === block.schedule.id,
            }"
            :title="tooltip(block.schedule)"
            :style="{
              gridColumn: block.gridColumn,
              gridRow: `${block.gridRowStart} / ${block.gridRowEnd}`,
              backgroundColor: paint(block.schedule),
              color: textOn(paint(block.schedule)),
            }"
            @pointerdown="onBlockDown($event, block.schedule)"
            @pointermove="onBlockMove"
            @pointerup="onBlockUp"
            @pointercancel="onBlockUp"
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
/* 화면 높이에 맞춰 하루치가 통째로 들어간다. 세로 스크롤은 두지 않는다.
   높이는 App 이 나눠 준 만큼 받는다 — 상단 바 높이를 여기서 짐작하지 않는다. */
.frame {
  display: flex;
  flex-direction: column;
  height: 100%;
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

/* 지금 그릴 수 있는 열. 아주 옅게 깔아 어디를 끌면 되는지 알린다. */
.lane.drawable {
  background: rgb(23 24 28 / 3%);
  cursor: crosshair;
}

.who.editing {
  color: var(--ink);
  font-weight: 700;
}

/* 손을 떼도 남아 있고, 잡아서 늘리거나 옮길 수 있다. ⊕ 를 밖에 내달아야
   해서 넘치는 것을 자르지 않는다 — 시간 글자만 따로 자른다. */
.draft {
  position: relative;
  z-index: 2;
  margin: 0 2px 1px 1px;
  padding-top: 3px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  border: 1.5px dashed var(--ink);
  border-radius: 4px;
  background: rgb(23 24 28 / 7%);
  font-family: var(--mono);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  cursor: move;
  touch-action: none;
}

/* 잡고 있는 동안 조금 진해져서 손에 들렸다는 것을 알린다. */
.draft.held {
  background: rgb(23 24 28 / 13%);
}

.draft-time {
  overflow: hidden;
  white-space: nowrap;
  pointer-events: none;
}

/* 위아래 끝. 짧은 초안에서는 둘이 만나 가운데가 없어지지 않게 줄인다. */
.draft-edge {
  position: absolute;
  right: 0;
  left: 0;
  height: 12px;
  max-height: 34%;
  cursor: ns-resize;
  touch-action: none;
}

.draft-edge--top {
  top: 0;
}

.draft-edge--bottom {
  bottom: 0;
}

/* 손가락으로는 12px 을 집기 어렵다. */
@media (pointer: coarse) {
  .draft-edge {
    height: 16px;
  }
}

/* 초안 오른쪽 바깥, 세로 가운데. 초안이 짧든 길든 늘 같은 자리다. */
.draft-add {
  position: absolute;
  top: 50%;
  right: -30px;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  transform: translateY(-50%);
  border: 1px solid var(--rule-strong);
  border-radius: 50%;
  background: var(--paper);
  color: var(--ink);
  cursor: pointer;
}

.draft-add:hover {
  background: var(--ink);
  color: var(--paper);
}

/* 맨 오른쪽 열에서는 왼쪽에 단다. 그대로 두면 화면 밖으로 밀린다. */
.draft-add--flip {
  right: auto;
  left: -30px;
}

.draft-add svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 2;
  stroke-linecap: round;
}

/* 이미 있는 일정과 겹친다. 이대로는 저장할 수 없다.
   바탕을 비쳐 두어야 무엇과 부딪혔는지 아래로 보인다. */
.draft.clash {
  border-color: var(--alarm);
  background: color-mix(in srgb, var(--alarm) 14%, transparent);
  color: var(--alarm);
}

/* Ctrl 을 누르고 있다. 원본을 두고 하나 더 만드는 중이라 실선으로 구분한다. */
.draft.copying {
  border-style: solid;
}

.draft-add:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.draft-add:disabled:hover {
  background: var(--paper);
  color: var(--ink);
}

/* 수정 중인 본인 일정은 잡아서 옮길 수 있다. */
.block.grabbable {
  cursor: grab;
}

.block.grabbable:active {
  cursor: grabbing;
}

/* 옮기는 동안 원래 자리를 흐려 어디서 떠나왔는지 남긴다. */
.block.ghost {
  opacity: 0.3;
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
