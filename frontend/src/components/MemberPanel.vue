<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import type { Member } from '@/types'

/** 좁은 화면에서 서랍이 열려 있는지. 넓은 화면 배치에는 영향이 없다. */
defineProps<{ open?: boolean }>()

const store = useBoardStore()

/** 드래그는 배열을 직접 뒤집으므로 스토어가 아닌 사본 위에서 다룬다. */
const groups = ref<Record<number, Member[]>>({})
const saving = ref(false)
/** 끌고 있는 동안만 놓을 수 있는 자리를 옅게 드러낸다. */
const dragging = ref(false)

function rebuild() {
  const next: Record<number, Member[]> = {}
  for (const category of store.sortedCategories) {
    next[category.id] = store.membersOf(category.id)
  }
  groups.value = next
}

watch(() => [store.categories, store.members], rebuild, {
  immediate: true,
  deep: true,
})

/**
 * 드래그가 끝나면 소속을 먼저 모두 옮기고, 그다음 순서를 확정한다.
 * 순서 API는 그 카테고리의 전체 멤버 집합을 요구하므로 순서가 뒤바뀌면 안 된다.
 */
async function commitAll() {
  dragging.value = false
  if (saving.value) {
    return
  }
  saving.value = true
  const creds = store.credentialsFor()
  try {
    for (const category of store.sortedCategories) {
      for (const member of groups.value[category.id] ?? []) {
        if (member.category_id !== category.id) {
          await api.updateMember(member.id, { category_id: category.id }, creds)
        }
      }
    }
    for (const category of store.sortedCategories) {
      const ids = (groups.value[category.id] ?? []).map((m) => m.id)
      await api.reorderMembers(category.id, ids, creds)
    }
  } catch (err) {
    store.reportError(err)
  } finally {
    saving.value = false
    await store.fetchBoard()
  }
}
</script>

<template>
  <aside class="side" :class="{ folded: store.sideFolded, dragging, open }">
    <!-- 목록 오른쪽 위. 접으면 가르는 선 옆으로 나와 펴는 손잡이가 된다. -->
    <button
      type="button"
      class="fold"
      :title="store.sideFolded ? '이름 목록 펴기' : '이름 목록 접어 표 넓히기'"
      :aria-label="store.sideFolded ? '이름 목록 펴기' : '이름 목록 접기'"
      :aria-expanded="!store.sideFolded"
      @click="store.toggleSide()"
    >
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path
          :d="
            store.sideFolded
              ? 'M7 4.5 12.5 10 7 15.5M12.5 4.5 18 10l-5.5 5.5'
              : 'M13 4.5 7.5 10l5.5 5.5M7.5 4.5 2 10l5.5 5.5'
          "
        />
      </svg>
    </button>

    <!-- 접힐 때 이 안쪽은 폭을 그대로 두고 잘려 나간다. 같이 좁아지면
         이름 칸이 찌그러지면서 접히는 것이 아니라 뭉개져 보인다. -->
    <div class="inner">
      <div class="scroll">
      <section
        v-for="category in store.sortedCategories"
        :key="category.id"
        class="group"
      >
        <h2>{{ category.name }}</h2>

        <!-- 손가락에서는 길게 눌러야(250ms) 끌기가 시작된다. 탭은 손끝이
             몇 px 씩 흔들리기 마련이라, 그대로 두면 고르려던 이름이 들려
             움직인다. 마우스는 흔들리지 않으므로 기다리지 않는다. -->
        <draggable
          v-model="groups[category.id]"
          class="names"
          group="members"
          item-key="id"
          :animation="180"
          :force-fallback="true"
          :fallback-on-body="true"
          :delay="250"
          :delay-on-touch-only="true"
          :touch-start-threshold="6"
          ghost-class="ghost"
          chosen-class="chosen"
          drag-class="flying"
          @start="dragging = true"
          @end="commitAll"
        >
          <template #item="{ element }">
            <button
              type="button"
              class="name"
              :class="{ on: store.selectedIds.includes(element.id) }"
              :title="element.name"
              @click="store.toggleSelection(element.id)"
            >
              {{ element.name }}
            </button>
          </template>
          <template #footer>
            <p v-if="(groups[category.id] ?? []).length === 0" class="none">
              아직 없음
            </p>
          </template>
        </draggable>
      </section>
      </div>

      <div class="foot">
        <!-- 짝을 이루는 두 동작이라 한 덩어리로 묶는다. -->
        <div class="seg">
          <button type="button" class="seg-btn" @click="store.selectAll()">
            전체
          </button>
          <button type="button" class="seg-btn" @click="store.clearSelection()">
            해제
          </button>
        </div>
        <span class="count">{{ store.selectedIds.length }}명 보는 중</span>
      </div>

      <p class="admin-hint">끌어서 순서와 소속을 바꿉니다</p>
    </div>
  </aside>
</template>

<style scoped>
.side {
  position: relative;
  width: 240px;
  flex: 0 0 240px;
  overflow: hidden;
  border-right: 1px solid var(--rule);
  transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1),
    flex-basis 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* 접히는 동안에도 안쪽은 제 폭을 지키고 잘려 나간다. 같이 좁아지면
   이름 칸이 찌그러지면서 접히는 게 아니라 뭉개져 보인다. */
.inner {
  display: flex;
  flex-direction: column;
  width: 240px;
  transition: opacity 200ms ease;
}

/* 접으면 화살표 한 개 폭만 남기고 나머지를 표에 내준다.
   폭을 0 으로 두면 화살표가 칸 밖으로 나가 표 테두리를 밟는다. */
.side.folded {
  width: 24px;
  flex: 0 0 24px;
}

.side.folded .inner {
  opacity: 0;
  pointer-events: none;
}

/* 상자를 두르지 않는다. 첫 카테고리 이름과 같은 줄에 겹화살표만 선다.
   « 글자를 쓰면 글리프가 작게 그려져, 획을 직접 그린다. */
/* 오른쪽 끝에 붙여 두면 칸이 좁아질 때 따로 옮기지 않아도 함께 밀려온다 —
   접힌 24px 칸에서는 이 자리가 곧 왼쪽 끝이다. */
.fold {
  position: absolute;
  top: 0;
  right: 2px;
  z-index: 5;
  display: grid;
  place-items: center;
  padding: 2px;
  border: 0;
  background: none;
  color: var(--mute);
  cursor: pointer;
  transition: color 110ms ease;
}

.fold svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.fold:hover {
  color: var(--ink);
}

.scroll {
  flex: 1;
  overflow-y: auto;
  padding: 2px 14px 8px 0;
}

.group + .group {
  margin-top: 18px;
}

h2 {
  margin: 0 0 8px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--mute);
}

/* 이름은 한 줄에 셋씩. 좁아지면 알아서 두 줄이 된다. */
.names {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  min-height: 30px;
}

/* 채워진 박스는 지금 표에 보이는 사람이다. 기호 없이 박스 하나로 말한다. */
.name {
  font: inherit;
  font-size: 12.5px;
  padding: 7px 6px;
  border: 1px solid var(--rule-strong);
  border-radius: 11px;
  background: var(--paper);
  color: var(--mute);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: grab;
  transition: background 110ms ease, color 110ms ease, border-color 110ms ease;
}

.name:hover {
  border-color: var(--ink-soft);
  color: var(--ink);
}

.name.on {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper);
}

/* ── 끌어 옮기는 동안 ─────────────────────────────────────────
   Sortable 이 세 요소에 각각 클래스를 붙인다. 자리를 비켜 주는
   움직임(animation)과 함께, 무엇을 들었고 어디에 놓이는지 보인다. */

/* 놓일 자리. 이름을 남겨 무엇이 그 자리에 들어가는지 알린다.
   바탕을 옅게 칠하고 테두리를 진한 점선으로 둬야 목록 안에서 도드라진다. */
.name.ghost {
  background: color-mix(in srgb, var(--ink) 7%, var(--paper));
  border: 1.5px dashed var(--ink-soft);
  color: var(--ink-soft);
}

.name.chosen {
  cursor: grabbing;
}

/* 손끝을 따라다니는 쪽. 종이에서 떠오른 만큼 그림자를 준다.
   이 복제본은 body 바로 아래에 붙으므로 부모를 앞세운 선택자로는 잡히지 않는다. */
.name.flying {
  border-color: var(--ink-soft);
  background: var(--paper);
  color: var(--ink);
  box-shadow: 0 10px 22px rgb(23 24 28 / 22%);
  opacity: 1;
}

/* 끄는 동안에만 놓을 수 있는 칸을 옅게 두른다. 빈 학년도 자리로 보인다. */
.side.dragging .names {
  outline: 1px dashed var(--rule);
  outline-offset: 5px;
  border-radius: 4px;
}

.none {
  grid-column: 1 / -1;
  margin: 0;
  padding: 4px 2px;
  font-size: 12px;
  color: var(--rule-strong);
}

.foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px 0 0;
  border-top: 1px solid var(--rule);
}

/* 이름 박스와 같은 둥근 모서리로 맞춰 한 벌처럼 보이게 한다. */
.seg {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--rule-strong);
  border-radius: 11px;
  background: var(--paper);
}

.seg-btn {
  font: inherit;
  font-size: 11.5px;
  padding: 5px 13px;
  border: 0;
  background: transparent;
  color: var(--mute);
  cursor: pointer;
  transition: background 110ms ease, color 110ms ease;
}

.seg-btn + .seg-btn {
  border-left: 1px solid var(--rule);
}

.seg-btn:hover {
  background: var(--wash);
  color: var(--ink);
}

.seg-btn:active {
  background: var(--ink);
  color: var(--paper);
}

.count {
  font-size: 11px;
  color: var(--mute);
  font-variant-numeric: tabular-nums;
}

.admin-hint {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--mute);
}

@media (max-width: 860px) {
  /* 좁은 화면에서는 목록이 왼쪽 서랍이 된다. 흐름에서 빠져 표가 화면을
     다 쓰고, 상단의 "이름" 단추로 밀어 연다. */
  .side {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 45;
    width: min(300px, 84vw);
    flex: none;
    padding: 16px 14px;
    overflow-y: auto;
    background: var(--page);
    border-right: 1px solid var(--rule);
    transform: translateX(-104%);
    transition: transform 260ms cubic-bezier(0.32, 0.72, 0, 1);
  }

  .side.open {
    transform: translateX(0);
    box-shadow: 14px 0 40px -18px rgb(23 24 28 / 35%);
  }

  @media (prefers-reduced-motion: reduce) {
    .side {
      transition: none;
    }
  }

  /* 서랍에는 접기 개념이 없다. 닫는 것은 스크림이 맡는다. */
  .fold {
    display: none;
  }

  .side.folded {
    width: min(300px, 84vw);
    flex: none;
  }

  .inner {
    width: 100%;
    transition: none;
  }

  .side.folded .inner {
    opacity: 1;
    pointer-events: auto;
  }

  .scroll {
    max-height: none;
    padding-right: 0;
  }

  /* 서랍 폭에서는 한 줄에 둘이 알맞다. */
  .names {
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  }

  .foot {
    padding-right: 0;
  }
}
</style>
