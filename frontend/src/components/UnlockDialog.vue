<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{
  mode: 'member' | 'admin'
  /** 확인할 이름. 수정 버튼이 고른 사람이라 고를 필요가 없다. */
  memberId?: number
}>()
const emit = defineEmits<{ close: []; unlocked: [memberId: number] }>()

const store = useBoardStore()
const password = ref('')
const message = ref('')
const busy = ref(false)

const target = computed(() =>
  props.memberId === undefined ? null : store.memberById(props.memberId),
)

async function submit() {
  message.value = ''
  busy.value = true
  try {
    if (props.mode === 'admin') {
      await store.unlockAdmin(password.value)
    } else if (props.memberId === undefined) {
      message.value = '이름이 지정되지 않았습니다.'
      return
    } else {
      await store.unlockMember(props.memberId, password.value)
      emit('unlocked', props.memberId)
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
    :title="mode === 'admin' ? '관리자 확인' : `${target?.name ?? ''} 확인`"
    @close="emit('close')"
  >
    <form class="stack" @submit.prevent="submit">
      <p class="notice notice--quiet">
        {{
          mode === 'admin'
            ? '관리자 비밀번호를 넣으면 모든 일정과 카테고리를 고칠 수 있습니다.'
            : '등록할 때 정한 숫자 4자리를 넣으면 이 이름의 시간표를 고칠 수 있습니다.'
        }}
      </p>

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
          autofocus
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
