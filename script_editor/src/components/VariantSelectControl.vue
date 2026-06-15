<script setup lang="ts">
import { X } from "@lucide/vue";

const props = defineProps<{
  field: string;
  values: unknown[];
  selected: string;
  optionLabel: (field: string, value: unknown, index: number) => string;
}>();

const emit = defineEmits<{
  change: [index: string];
  remove: [];
}>();

function handleChange(event: Event) {
  emit("change", (event.target as HTMLSelectElement).value);
}
</script>

<template>
  <div class="variant-control">
    <button
      class="variant-remove"
      title="删除当前版本"
      type="button"
      @click="emit('remove')"
    >
      <X :size="14" aria-hidden="true" />
    </button>
    <select :value="props.selected" class="variant-select" @change="handleChange">
      <option v-for="(value, index) in props.values" :key="`${props.field}-${index}`" :value="index">
        {{ props.optionLabel(props.field, value, index) }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.variant-control {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 6px;
  align-items: center;
}

.variant-remove {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.variant-remove:hover {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
  transform: translateY(-1px);
}

.variant-remove:active {
  transform: scale(var(--motion-press-scale));
}

.variant-select {
  width: 100%;
  height: 36px;
  padding: 0 10px;
  border: 1px solid #d8d8d8;
  border-radius: 9px;
  background: #ffffff;
  color: #111111;
  outline: none;
  transition:
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard),
    background var(--motion-duration-fast) var(--motion-ease-standard);
}

.variant-select:focus {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}
</style>
