<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{ mode: 'member' | 'admin' }>()
const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const memberId = ref<number | null>(store.activeMemberId)
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  try {
    if (props.mode === 'admin') {
      await store.unlockAdmin(password.value)
    } else if (memberId.value === null) {
      message.value = '이름을 선택해 주세요.'
      return
    } else {
      await store.unlockMember(memberId.value, password.value)
    }
    emit('close')
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '확인에 실패했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog
    :title="mode === 'admin' ? '관리자 모드' : '내 이름 잠금 해제'"
    @close="emit('close')"
  >
    <form @submit.prevent="submit">
      <label v-if="mode === 'member'">
        이름
        <select v-model.number="memberId">
          <option :value="null" disabled>선택하세요</option>
          <option
            v-for="member in store.orderedMembers"
            :key="member.id"
            :value="member.id"
          >
            {{ member.name }}
          </option>
        </select>
      </label>

      <label>
        비밀번호
        <input
          v-model="password"
          :type="mode === 'admin' ? 'password' : 'text'"
          :inputmode="mode === 'admin' ? undefined : 'numeric'"
          :maxlength="mode === 'admin' ? undefined : 4"
          :placeholder="mode === 'admin' ? '관리자 비밀번호' : '숫자 4자리'"
          autocomplete="off"
        />
      </label>

      <p v-if="message" class="message">{{ message }}</p>

      <div class="actions">
        <button type="button" @click="emit('close')">취소</button>
        <button type="submit" class="primary" :disabled="busy">확인</button>
      </div>
    </form>
  </BaseDialog>
</template>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--muted);
}

input,
select {
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text);
}

.message {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.actions button {
  padding: 8px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--surface);
}

.actions .primary {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}
</style>
