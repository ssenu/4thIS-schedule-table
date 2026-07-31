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
      message.value = '이름을 골라 주세요.'
      return
    } else {
      await store.unlockMember(memberId.value, password.value)
    }
    emit('close')
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '확인하지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog
    :title="mode === 'admin' ? '관리자 확인' : '내 이름 확인'"
    @close="emit('close')"
  >
    <form class="stack" @submit.prevent="submit">
      <p class="notice notice--quiet">
        {{
          mode === 'admin'
            ? '관리자 비밀번호를 넣으면 모든 일정과 카테고리를 고칠 수 있습니다.'
            : '비밀번호를 넣으면 그 이름의 일정을 고칠 수 있습니다.'
        }}
      </p>

      <label v-if="mode === 'member'" class="field">
        <span>이름</span>
        <select v-model.number="memberId" class="select">
          <option :value="null" disabled>고르세요</option>
          <option
            v-for="member in store.orderedMembers"
            :key="member.id"
            :value="member.id"
          >
            {{ member.name }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>비밀번호</span>
        <input
          v-model="password"
          class="input"
          :type="mode === 'admin' ? 'password' : 'text'"
          :inputmode="mode === 'admin' ? undefined : 'numeric'"
          :maxlength="mode === 'admin' ? undefined : 4"
          :placeholder="mode === 'admin' ? '관리자 비밀번호' : '숫자 4자리'"
          autocomplete="off"
        />
      </label>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <div class="row-end">
        <span class="spacer" />
        <button type="button" class="btn" @click="emit('close')">취소</button>
        <button type="submit" class="btn btn--primary" :disabled="busy">
          확인
        </button>
      </div>
    </form>
  </BaseDialog>
</template>
