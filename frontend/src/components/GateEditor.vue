<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, api } from '@/api/client'
import { useBoardStore } from '@/stores/board'
import BaseDialog from './BaseDialog.vue'

const emit = defineEmits<{ close: [] }>()

const store = useBoardStore()
const title = ref(store.gateTitle)
const intro = ref(store.gateIntro)
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  const body: { title?: string; intro?: string; password?: string } = {}
  if (title.value.trim() !== store.gateTitle) {
    body.title = title.value.trim()
  }
  if (intro.value !== store.gateIntro) {
    body.intro = intro.value
  }
  if (password.value) {
    body.password = password.value
  }
  try {
    if (Object.keys(body).length > 0) {
      const saved = await api.updateGate(body, store.credentialsFor())
      // 새 비밀번호부터 손에 쥔다. 서버는 저장하는 순간 옛 비밀번호를
      // 버리므로, 이 사이에 다른 요청이 나가면 내가 문 밖으로 밀려난다.
      if (body.password) {
        store.adoptGatePassword(body.password)
      }
      store.gateTitle = saved.title
      store.gateIntro = saved.intro
    }
    emit('close')
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '저장하지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseDialog title="입장 설정" wide @close="emit('close')">
    <p v-if="!store.isAdmin" class="notice notice--quiet">
      관리자만 바꿀 수 있습니다.
    </p>

    <form v-else class="stack" @submit.prevent="submit">
      <p class="notice notice--quiet">
        사이트에 들어올 때 보이는 화면입니다.
      </p>

      <label class="field">
        <span>제목</span>
        <input v-model="title" class="input" maxlength="40" autocomplete="off" />
      </label>

      <label class="field">
        <span>설명</span>
        <textarea v-model="intro" class="input intro" maxlength="500" rows="4" />
      </label>

      <label class="field">
        <span>새 입장 비밀번호</span>
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="바꿀 때만 채우세요 (4자 이상)"
          autocomplete="new-password"
        />
      </label>

      <p v-if="password" class="notice notice--warn">
        바꾸면 동아리원 모두가 다시 입력해야 합니다.
      </p>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>

      <div class="row-end">
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
.intro {
  resize: vertical;
  line-height: 1.5;
  font-family: inherit;
}
</style>
