<script setup lang="ts">
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()
</script>

<template>
  <div v-if="store.error" class="banner" role="alert">
    <span>{{ store.error }}</span>
    <button type="button" @click="store.error = ''">닫기</button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

button {
  border: 1px solid #991b1b;
  border-radius: 5px;
  background: none;
  color: inherit;
  padding: 2px 8px;
  font-size: 12px;
}
</style>
