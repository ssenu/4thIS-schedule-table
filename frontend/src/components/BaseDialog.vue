<script setup lang="ts">
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <header>
        <h2>{{ title }}</h2>
        <button type="button" class="x" aria-label="닫기" @click="emit('close')">
          ✕
        </button>
      </header>
      <div class="body">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(15 23 42 / 45%);
}

.dialog {
  width: min(460px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: var(--surface);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgb(0 0 0 / 25%);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line-soft);
}

h2 {
  margin: 0;
  font-size: 16px;
}

.x {
  border: none;
  background: none;
  font-size: 16px;
  color: var(--muted);
}

.body {
  padding: 16px;
}
</style>
