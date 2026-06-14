<script setup lang="ts">
import type { FormatState, TextColorOption } from "./previewTypes";

defineProps<{
  visible: boolean;
  formatState: FormatState;
  textColorOptions: TextColorOption[];
  backgroundColorOptions: TextColorOption[];
  isTextColorActive: (option: TextColorOption) => boolean;
  isBackgroundColorActive: (option: TextColorOption) => boolean;
}>();

const emit = defineEmits<{
  "inline-command": [command: "bold" | "italic" | "underline"];
  "text-color": [option: TextColorOption];
  "background-color": [option: TextColorOption];
}>();
</script>

<template>
  <Transition name="format-toolbar">
    <div
      v-if="visible"
      class="text-format-toolbar"
      aria-label="文字格式工具栏"
      @mousedown.prevent
    >
      <div class="toolbar-button-group" aria-label="字形">
        <button
          :class="['format-command', 'bold', { active: formatState.bold }]"
          type="button"
          title="加粗"
          :aria-pressed="formatState.bold"
          @mousedown.prevent.stop="emit('inline-command', 'bold')"
        >
          B
        </button>
        <button
          :class="['format-command', 'italic', { active: formatState.italic }]"
          type="button"
          title="斜体"
          :aria-pressed="formatState.italic"
          @mousedown.prevent.stop="emit('inline-command', 'italic')"
        >
          I
        </button>
        <button
          :class="['format-command', 'underline', { active: formatState.underline }]"
          type="button"
          title="下划线"
          :aria-pressed="formatState.underline"
          @mousedown.prevent.stop="emit('inline-command', 'underline')"
        >
          U
        </button>
      </div>
      <div class="toolbar-swatch-group" aria-label="文字颜色">
        <button
          v-for="option in textColorOptions"
          :key="`text-${option.label}`"
          :class="['format-swatch', { active: isTextColorActive(option), clear: option.color === 'transparent' }]"
          type="button"
          :title="`文字颜色：${option.label}`"
          :style="{ '--swatch-color': option.color }"
          :aria-pressed="isTextColorActive(option)"
          @mousedown.prevent.stop="emit('text-color', option)"
        />
      </div>
      <div class="toolbar-swatch-group background" aria-label="背景颜色">
        <button
          v-for="option in backgroundColorOptions"
          :key="`background-${option.label}`"
          :class="['format-swatch', { active: isBackgroundColorActive(option), clear: option.color === 'transparent' }]"
          type="button"
          :title="`背景颜色：${option.label}`"
          :style="{ '--swatch-color': option.color }"
          :aria-pressed="isBackgroundColorActive(option)"
          @mousedown.prevent.stop="emit('background-color', option)"
        />
      </div>
    </div>
  </Transition>
</template>
