declare module 'vuedraggable' {
  import type { DefineComponent } from 'vue'

  const draggable: DefineComponent<
    { list?: unknown[]; group?: unknown; itemKey?: string; disabled?: boolean },
    Record<string, unknown>,
    unknown
  >
  export default draggable
}
