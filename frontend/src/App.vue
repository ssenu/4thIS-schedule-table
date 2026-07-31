<script setup lang="ts">
import { onMounted } from 'vue'
import ScheduleGrid from '@/components/ScheduleGrid.vue'
import { useBoardStore } from '@/stores/board'

const store = useBoardStore()

onMounted(async () => {
  store.restore()
  await store.fetchBoard()
})
</script>

<template>
  <main class="app">
    <h1>동아리 주간 시간표</h1>

    <div class="toolbar">
      <button type="button" @click="store.selectAll()">전체 보기</button>
      <button type="button" @click="store.clearSelection()">선택 해제</button>
      <span v-if="store.loading" class="muted">불러오는 중…</span>
    </div>

    <p v-if="store.error" class="error">{{ store.error }}</p>

    <ScheduleGrid
      :members="store.selectedMembers"
      :schedules="store.visibleSchedules"
    />
  </main>
</template>

<style scoped>
.app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
}

h1 {
  font-size: 20px;
  margin: 0 0 12px;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.muted {
  color: var(--muted);
  font-size: 13px;
}

.error {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}
</style>
