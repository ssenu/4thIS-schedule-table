<script setup lang="ts">
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
</script>

<template>
  <div v-if="store.error" class="banner" role="alert">
    <span>{{ store.error }}</span>
    <button type="button" class="btn btn--sm" @click="store.error = ''">
      닫기
    </button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 9px 10px 9px 12px;
  border-radius: 4px;
  background: var(--alarm-wash);
  color: var(--alarm);
  font-size: 12.5px;
}

.btn {
  border-color: color-mix(in srgb, var(--alarm) 35%, transparent);
  background: transparent;
  color: inherit;
}

.btn:hover {
  border-color: var(--alarm);
  background: transparent;
}
</style>
