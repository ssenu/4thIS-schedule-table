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
                mine: store.canEdit(element.id),
                grab: store.isAdmin,
              }"
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
  width: 168px;
  flex: 0 0 168px;
  border-right: 1px solid var(--rule);
}

.scroll {
  flex: 1;
  overflow-y: auto;
  padding: 2px 12px 8px 0;
}

.group + .group {
  margin-top: 18px;
}

h2 {
  margin: 0 0 6px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--mute);
}

.names {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-height: 22px;
}

/*
 * 두 가지를 한 줄로 말한다.
 * 네모가 차 있으면 표에 보이는 사람, 글씨가 굵으면 내가 고칠 수 있는 사람.
 */
.name {
  font: inherit;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 4px 6px;
  border: none;
  border-radius: 4px;
  background: none;
  color: var(--mute);
  text-align: left;
  cursor: pointer;
  transition: background 110ms ease, color 110ms ease;
}

.name::before {
  content: "";
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  border: 1px solid var(--rule-strong);
  border-radius: 2px;
}

.name:hover {
  background: rgb(23 24 28 / 5%);
}

.name.on {
  color: var(--ink);
}

.name.on::before {
  background: var(--ink);
  border-color: var(--ink);
}

.name.mine {
  font-weight: 650;
}

.name.grab {
  cursor: grab;
}

.none {
  margin: 0;
  padding: 4px 6px;
  font-size: 12px;
  color: var(--rule-strong);
}

.foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px 0 0;
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
    max-height: 208px;
    padding-right: 0;
  }

  .foot {
    padding-right: 0;
  }
}
</style>
