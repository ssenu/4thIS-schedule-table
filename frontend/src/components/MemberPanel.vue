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
  <aside class="side">
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
                mine: store.unlocked[element.id] !== undefined,
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
      <button type="button" class="btn btn--sm" @click="store.selectAll()">
        전체
      </button>
      <button type="button" class="btn btn--sm" @click="store.clearSelection()">
        해제
      </button>
      <span class="count">{{ store.selectedIds.length }}명 보는 중</span>
    </div>

    <p v-if="store.isAdmin" class="admin-hint">
      끌어서 순서와 소속을 바꿉니다
    </p>
  </aside>
</template>

<style scoped>
.side {
  display: flex;
  flex-direction: column;
  width: 240px;
  flex: 0 0 240px;
  border-right: 1px solid var(--rule);
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

/*
 * 채워진 박스는 표에 보이는 사람, 굵은 글씨는 내가 비밀번호를 넣어 둔 이름이다.
 * 두 가지를 기호 없이 박스 하나로 말한다. (관리자는 모두를 고칠 수 있지만
 * 그건 굵기로 말하지 않는다 — 전부 굵어지면 아무것도 구분하지 못한다.)
 */
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

.name.mine {
  font-weight: 700;
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
