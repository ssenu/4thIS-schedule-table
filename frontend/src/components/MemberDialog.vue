<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { NAME_MAX_LEN } from '@/constants'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ mode: 'create' | 'edit'; memberId?: number }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const target = computed(() =>
  props.memberId === undefined ? null : store.memberById(props.memberId),
)

const name = ref(target.value?.name ?? '')
const categoryId = ref<number>(
  target.value?.category_id ?? store.sortedCategories[0]?.id ?? 0,
)
const password = ref('')
const message = ref('')
const busy = ref(false)
const confirmingDelete = ref(false)

function fail(err: unknown) {
  message.value = err instanceof ApiError ? err.message : '요청이 실패했습니다.'
}

async function create() {
  const created = await api.createMember({
    name: name.value.trim(),
    category_id: categoryId.value,
    password: password.value,
  })
  await store.fetchBoard()
  // 방금 만든 사람은 바로 자기 시간표를 쓸 수 있어야 한다.
  await store.unlockMember(created.id, password.value)
}

async function update() {
  const current = target.value
  if (current === null) {
    return
  }
  const body: { name?: string; password?: string; category_id?: number } = {}
  if (name.value.trim() !== current.name) {
    body.name = name.value.trim()
  }
  if (password.value) {
    body.password = password.value
  }
  if (store.isAdmin && categoryId.value !== current.category_id) {
    body.category_id = categoryId.value
  }
  if (Object.keys(body).length === 0) {
    return
  }
  await api.updateMember(current.id, body, store.credentialsFor(current.id))
  // 본인 자격으로 비밀번호를 바꿨다면 저장해 둔 값도 갱신해야 계속 편집할 수 있다.
  if (body.password && store.unlocked[current.id] !== undefined) {
    store.unlocked[current.id] = body.password
    store.persist()
  }
  await store.fetchBoard()
}

async function submit() {
  message.value = ''
  busy.value = true
  try {
    if (props.mode === 'create') {
      await create()
    } else {
      await update()
    }
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}

async function remove() {
  const current = target.value
  if (current === null) {
    return
  }
  message.value = ''
  busy.value = true
  try {
    await api.deleteMember(current.id, store.credentialsFor(current.id))
    await store.fetchBoard()
    emit('close')
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog
    :title="mode === 'create' ? '이름 등록' : '이름 수정'"
    @close="emit('close')"
  >
    <form class="stack" @submit.prevent="submit">
      <p v-if="mode === 'create'" class="notice notice--quiet">
        비밀번호는 내 일정을 남이 고치지 못하게 막습니다. 숫자 4자리면 됩니다.
      </p>

      <label class="field">
        <span>이름</span>
        <input
          v-model="name"
          class="input"
          :maxlength="NAME_MAX_LEN"
          autocomplete="off"
        />
      </label>

      <label v-if="mode === 'create' || store.isAdmin" class="field">
        <span>카테고리</span>
        <select v-model.number="categoryId" class="select">
          <option
            v-for="category in store.sortedCategories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <p v-else class="notice notice--quiet">
        소속은 관리자가 바꿉니다.
      </p>

      <label class="field">
        <span>{{ mode === 'create' ? '비밀번호' : '새 비밀번호' }}</span>
        <input
          v-model="password"
          class="input"
          type="password"
          inputmode="numeric"
          maxlength="4"
          :placeholder="mode === 'create' ? '숫자 4자리' : '바꿀 때만 채우세요'"
          autocomplete="off"
        />
      </label>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <p v-if="confirmingDelete" class="notice notice--warn confirm">
        <span>{{ target?.name }} 님의 이름과 일정을 모두 지웁니다.</span>
        <button
          type="button"
          class="btn btn--sm"
          @click="confirmingDelete = false"
        >
          그만두기
        </button>
        <button
          type="button"
          class="btn btn--sm btn--fill-danger"
          :disabled="busy"
          @click="remove"
        >
          지웁니다
        </button>
      </p>

      <div class="row-end">
        <button
          v-if="mode === 'edit' && !confirmingDelete"
          type="button"
          class="btn btn--danger"
          @click="confirmingDelete = true"
        >
          삭제
        </button>
        <span class="spacer" />
        <button type="button" class="btn" @click="emit('close')">취소</button>
        <button type="submit" class="btn btn--primary" :disabled="busy">
          저장
        </button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
.confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.confirm > span {
  flex: 1 1 100%;
}
</style>
