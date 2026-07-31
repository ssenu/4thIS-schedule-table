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

async function run(work: () => Promise<void>) {
  message.value = ''
  busy.value = true
  try {
    await work()
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '요청이 실패했습니다.'
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
  <BaseDialog title="카테고리" wide @close="emit('close')">
    <p v-if="!store.isAdmin" class="notice notice--quiet">
      관리자만 바꿀 수 있습니다.
    </p>

    <template v-else>
      <p class="notice notice--quiet head">
        끌어서 순서를 바꿉니다. 이름 칸을 고치면 바로 반영됩니다.
      </p>

      <draggable
        v-model="list"
        item-key="id"
        tag="ol"
        class="rows"
        @end="commitOrder"
      >
        <template #item="{ element }">
          <li>
            <span class="grip" aria-hidden="true">⠿</span>
            <input
              class="input"
              :value="element.name"
              :maxlength="NAME_MAX_LEN"
              @change="rename(element, ($event.target as HTMLInputElement).value)"
            />
            <span class="count">{{ store.membersOf(element.id).length }}명</span>

            <template v-if="pendingDelete === element.id">
              <button
                type="button"
                class="btn btn--sm"
                @click="pendingDelete = null"
              >
                그만두기
              </button>
              <button
                type="button"
                class="btn btn--sm btn--fill-danger"
                :disabled="busy"
                @click="remove(element)"
              >
                지웁니다
              </button>
            </template>
            <button
              v-else
              type="button"
              class="btn btn--sm btn--danger"
              @click="pendingDelete = element.id"
            >
              삭제
            </button>
          </li>
        </template>
      </draggable>

      <form class="row-end add" @submit.prevent="add">
        <input
          v-model="newName"
          class="input"
          :maxlength="NAME_MAX_LEN"
          placeholder="새 카테고리 이름"
        />
        <button type="submit" class="btn btn--primary" :disabled="busy">
          추가
        </button>
      </form>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>
    </template>
  </BaseDialog>
</template>

<style scoped>
.head {
  margin-bottom: 12px;
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--rule);
}

.rows li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 2px;
  border-bottom: 1px solid var(--rule);
}

.grip {
  cursor: grab;
  color: var(--rule-strong);
  font-size: 13px;
  user-select: none;
}

.count {
  flex: 0 0 auto;
  font-size: 11.5px;
  color: var(--mute);
  font-variant-numeric: tabular-nums;
}

.add {
  margin-top: 16px;
}
</style>
