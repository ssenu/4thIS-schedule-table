<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import { ApiError, api } from '@/api/client'
import { NAME_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import type { Category } from '@/types'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const list = ref<Category[]>([])
const newName = ref('')
const message = ref('')
const busy = ref(false)
const pendingDelete = ref<number | null>(null)

watch(
  () => store.categories,
  () => {
    list.value = store.sortedCategories
  },
  { immediate: true, deep: true },
)

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청에 실패했습니다.'
}

async function run(work: () => Promise<void>) {
  message.value = ''
  busy.value = true
  try {
    await work()
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
    await store.fetchBoard()
  }
}

async function add() {
  const name = newName.value.trim()
  if (!name) {
    return
  }
  await run(async () => {
    await api.createCategory(name, store.credentialsFor())
    newName.value = ''
  })
}

async function rename(category: Category, value: string) {
  const name = value.trim()
  if (!name || name === category.name) {
    return
  }
  await run(async () => {
    await api.renameCategory(category.id, name, store.credentialsFor())
  })
}

async function remove(category: Category) {
  await run(async () => {
    await api.deleteCategory(category.id, store.credentialsFor())
    pendingDelete.value = null
  })
}

async function commitOrder() {
  await run(async () => {
    await api.reorderCategories(
      list.value.map((category) => category.id),
      store.credentialsFor(),
    )
  })
}
</script>

<template>
  <BaseDialog title="카테고리 관리" @close="emit('close')">
    <p v-if="!store.isAdmin" class="hint">관리자 모드에서만 바꿀 수 있습니다.</p>

    <template v-else>
      <draggable v-model="list" item-key="id" class="rows" tag="ol" @end="commitOrder">
        <template #item="{ element }">
          <li>
            <span class="grip" aria-hidden="true">⠿</span>
            <input
              :value="element.name"
              :maxlength="NAME_MAX_LEN"
              @change="rename(element, ($event.target as HTMLInputElement).value)"
            />
            <span class="count">{{ store.membersOf(element.id).length }}명</span>

            <template v-if="pendingDelete === element.id">
              <button type="button" @click="pendingDelete = null">아니오</button>
              <button
                type="button"
                class="danger"
                :disabled="busy"
                @click="remove(element)"
              >
                지웁니다
              </button>
            </template>
            <button
              v-else
              type="button"
              class="danger"
              @click="pendingDelete = element.id"
            >
              삭제
            </button>
          </li>
        </template>
      </draggable>

      <form class="add" @submit.prevent="add">
        <input
          v-model="newName"
          :maxlength="NAME_MAX_LEN"
          placeholder="새 카테고리 이름"
        />
        <button type="submit" class="primary" :disabled="busy">추가</button>
      </form>

      <p v-if="message" class="message">{{ message }}</p>
    </template>
  </BaseDialog>
</template>

<style scoped>
.hint {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--surface-alt);
  font-size: 13px;
}

.grip {
  cursor: grab;
  color: var(--muted);
}

.rows input,
.add input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text);
}

.count {
  flex: 0 0 auto;
  color: var(--muted);
}

.add {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.rows button,
.add button {
  padding: 6px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
  font-size: 12px;
}

.primary {
  border-color: var(--accent) !important;
  background: var(--accent) !important;
  color: #fff;
}

.danger {
  border-color: #dc2626 !important;
  color: #dc2626;
}

.message {
  margin: 12px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}
</style>
