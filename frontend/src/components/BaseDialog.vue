<script setup lang="ts">
defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div class="veil" @click.self="emit('close')">
    <div class="panel" :class="{ wide }" role="dialog" aria-modal="true">
      <header>
        <h2>{{ title }}</h2>
        <button
          type="button"
          class="btn btn--quiet btn--sm"
          aria-label="닫기"
          @click="emit('close')"
        >
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
.veil {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgb(23 24 28 / 38%);
}

.panel {
  width: min(430px, 100%);
  max-height: 88vh;
  overflow: auto;
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: 6px;
  box-shadow: 0 18px 44px rgb(23 24 28 / 18%);
}

.panel.wide {
  width: min(560px, 100%);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px 13px 18px;
  border-bottom: 1px solid var(--rule);
}

h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.body {
  padding: 18px;
}
</style>
