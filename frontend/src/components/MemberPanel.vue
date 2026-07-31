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
  <section class="panel">
    <p v-if="store.isAdmin" class="notice">
      관리자 모드입니다. 이름을 끌어 순서와 소속을 바꿀 수 있습니다.
    </p>

    <div
      v-for="category in store.sortedCategories"
      :key="category.id"
      class="group"
    >
      <h3>{{ category.name }}</h3>

      <draggable
        v-model="groups[category.id]"
        class="chips"
        group="members"
        item-key="id"
        :disabled="!store.isAdmin"
        @end="commitAll"
      >
        <template #item="{ element }">
          <button
            type="button"
            class="chip"
            :class="{
              on: store.selectedIds.includes(element.id),
              mine: store.canEdit(element.id),
              draggable: store.isAdmin,
            }"
            @click="store.toggleSelection(element.id)"
          >
            {{ store.selectedIds.includes(element.id) ? '☑' : '☐' }}
            {{ element.name }}
          </button>
        </template>
        <template #footer>
          <span v-if="(groups[category.id] ?? []).length === 0" class="empty">
            아직 등록된 이름이 없습니다
          </span>
        </template>
      </draggable>
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 8px;
}

.notice {
  margin: 0;
  font-size: 12px;
  color: var(--accent);
}

.group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

h3 {
  flex: 0 0 72px;
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
  min-height: 30px;
}

.chip {
  padding: 4px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--surface);
  font-size: 13px;
}

.chip.on {
  border-color: var(--accent);
  background: #eff6ff;
  color: var(--accent);
}

/* 내가 편집할 수 있는 이름은 밑줄로 구분한다. */
.chip.mine {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.chip.draggable {
  cursor: grab;
}

.empty {
  font-size: 13px;
  color: var(--muted);
}
</style>
