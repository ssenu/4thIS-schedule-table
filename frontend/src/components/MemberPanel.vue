<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import type { Member } from '@/types'

const store = useBoardStore()

/** 드래그는 배열을 직접 뒤집으므로 스토어가 아닌 사본 위에서 다룬다. */
const groups = ref<Record<number, Member[]>>({})
const saving = ref(false)

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
  if (!store.isAdmin || saving.value) {
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
  <aside class="side" :class="{ folded: store.sideFolded }">
    <!-- 표와 이름 목록을 가르는 선 위에 걸터앉는다. 접으면 이 손잡이만 남는다. -->
    <button
      type="button"
      class="fold"
      :title="store.sideFolded ? '이름 목록 펴기' : '이름 목록 접어 표 넓히기'"
      :aria-label="store.sideFolded ? '이름 목록 펴기' : '이름 목록 접기'"
      :aria-expanded="!store.sideFolded"
      @click="store.toggleSide()"
    >
      <svg
        viewBox="0 0 16 16"
        width="12"
        height="12"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path :d="store.sideFolded ? 'M6 3.5 10.5 8 6 12.5' : 'M10 3.5 5.5 8 10 12.5'" />
      </svg>
    </button>

    <div class="scroll">
      <section
        v-for="category in store.sortedCategories"
        :key="category.id"
        class="group"
      >
        <h2>{{ category.name }}</h2>

        <draggable
          v-model="groups[category.id]"
          class="names"
          group="members"
          item-key="id"
          :disabled="!store.isAdmin"
          @end="commitAll"
        >
          <template #item="{ element }">
            <button
              type="button"
              class="name"
              :class="{
                on: store.selectedIds.includes(element.id),
                grab: store.isAdmin,
              }"
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

    <p v-if="store.isAdmin" class="admin-hint">
      끌어서 순서와 소속을 바꿉니다
    </p>
  </aside>
</template>

<style scoped>
.side {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 240px;
  flex: 0 0 240px;
  border-right: 1px solid var(--rule);
}

/* 접으면 가르는 선 한 줄만 남고, 표가 그 폭을 가져간다. */
.side.folded {
  width: 0;
  flex: 0 0 0;
  padding: 0;
}

.side.folded .scroll,
.side.folded .foot,
.side.folded .admin-hint {
  display: none;
}

/* 세로 가운데가 아니라 고정 높이다. 접으면 목록이 사라져 이 칸의 높이가
   달라지는데, 가운데에 매달아 두면 접을 때마다 손잡이가 튄다. */
.fold {
  position: absolute;
  top: 96px;
  right: -11px;
  z-index: 5;
  display: grid;
  place-items: center;
  width: 21px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--rule);
  border-radius: 6px;
  background: var(--paper);
  color: var(--mute);
  cursor: pointer;
  transition: color 110ms ease, border-color 110ms ease;
}

.fold:hover {
  border-color: var(--rule-strong);
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
  cursor: pointer;
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

.name.grab {
  cursor: grab;
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
  .side {
    width: 100%;
    flex: none;
    padding-bottom: 12px;
    border-right: none;
    border-bottom: 1px solid var(--rule);
  }

  /* 좁은 화면에서는 목록이 표 위에 놓여 접을 이유가 없다.
     접어 둔 채로 들어와도 펴서 보여준다. */
  .fold {
    display: none;
  }

  .side.folded {
    width: 100%;
    flex: none;
  }

  .side.folded .scroll {
    display: block;
  }

  .side.folded .foot {
    display: flex;
  }

  .side.folded .admin-hint {
    display: block;
  }

  .scroll {
    max-height: 244px;
    padding-right: 0;
  }

  /* 폭이 넓어지므로 셋으로 묶어 둘 필요가 없다. */
  .names {
    grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  }

  .foot {
    padding-right: 0;
  }
}
</style>
