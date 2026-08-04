<script setup lang="ts">
import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
const password = ref('')
const message = ref('')
const busy = ref(false)

async function submit() {
  message.value = ''
  busy.value = true
  try {
    await store.enterGate(password.value)
    await store.fetchBoard()
  } catch (err) {
    message.value = err instanceof ApiError ? err.message : '들어가지 못했습니다.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="gate">
    <div class="card">
      <h1>{{ store.gateTitle }}</h1>
      <p v-if="store.gateIntro" class="intro">{{ store.gateIntro }}</p>

      <form @submit.prevent="submit">
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="비밀번호"
          autocomplete="current-password"
          aria-label="입장 비밀번호"
        />
        <button type="submit" class="btn btn--primary" :disabled="busy">
          들어가기
        </button>
      </form>

      <p v-if="message" class="notice notice--alarm">{{ message }}</p>
    </div>
  </main>
</template>

<style scoped>
.gate {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* 표가 없는 화면이라 여백을 넉넉히 두고 제목을 세운다. */
.card {
  width: min(420px, 100%);
  padding: 36px 32px 32px;
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: 10px;
}

h1 {
  margin: 0 0 14px;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.3;
}

/* 관리자가 넣은 줄바꿈을 그대로 살린다. */
.intro {
  margin: 0 0 24px;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--mute);
  white-space: pre-line;
}

form {
  display: flex;
  gap: 8px;
}

form .input {
  flex: 1;
}

form .btn {
  flex: 0 0 auto;
}

.notice {
  margin-top: 14px;
}
</style>
