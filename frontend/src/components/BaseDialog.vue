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
  animation: veil-in 150ms ease both;
}

.panel {
  width: min(430px, 100%);
  max-height: 88vh;
  overflow: auto;
  background: var(--paper);
  border: 1px solid rgb(23 24 28 / 16%);
  border-radius: 11px;
  box-shadow: 0 18px 44px rgb(23 24 28 / 18%);
  /* 뒷막보다 조금 늦게, 조금 길게 — 판이 뒤에서 올라오는 것으로 읽힌다. */
  animation: panel-in 220ms cubic-bezier(0.2, 0.85, 0.25, 1) both;
}

@keyframes veil-in {
  from {
    opacity: 0;
  }
}

@keyframes panel-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.985);
  }
}

/* 움직임을 줄여 달라고 한 사람에게는 그냥 나타난다. */
@media (prefers-reduced-motion: reduce) {
  .veil,
  .panel {
    animation: none;
  }
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
