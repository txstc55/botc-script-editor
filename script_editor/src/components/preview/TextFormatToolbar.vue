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
          tabindex="-1"
          :aria-pressed="formatState.bold"
          @pointerdown.prevent.stop="emit('inline-command', 'bold')"
          @mousedown.prevent.stop
          @click.prevent.stop
        >
          B
        </button>
        <button
          :class="['format-command', 'italic', { active: formatState.italic }]"
          type="button"
          title="斜体"
          tabindex="-1"
          :aria-pressed="formatState.italic"
          @pointerdown.prevent.stop="emit('inline-command', 'italic')"
          @mousedown.prevent.stop
          @click.prevent.stop
        >
          I
        </button>
        <button
          :class="['format-command', 'underline', { active: formatState.underline }]"
          type="button"
          title="下划线"
          tabindex="-1"
          :aria-pressed="formatState.underline"
          @pointerdown.prevent.stop="emit('inline-command', 'underline')"
          @mousedown.prevent.stop
          @click.prevent.stop
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
          tabindex="-1"
          :style="{ '--swatch-color': option.color }"
          :aria-pressed="isTextColorActive(option)"
          @pointerdown.prevent.stop="emit('text-color', option)"
          @mousedown.prevent.stop
          @click.prevent.stop
        />
      </div>
      <div class="toolbar-swatch-group background" aria-label="背景颜色">
        <button
          v-for="option in backgroundColorOptions"
          :key="`background-${option.label}`"
          :class="['format-swatch', { active: isBackgroundColorActive(option), clear: option.color === 'transparent' }]"
          type="button"
          :title="`背景颜色：${option.label}`"
          tabindex="-1"
          :style="{ '--swatch-color': option.color }"
          :aria-pressed="isBackgroundColorActive(option)"
          @pointerdown.prevent.stop="emit('background-color', option)"
          @mousedown.prevent.stop
          @click.prevent.stop
        />
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.text-format-toolbar {
  position: absolute;
  z-index: 20;
  left: 50%;
  bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  max-width: calc(100% - 32px);
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.14);
  transform: translateX(-50%);
  user-select: none;
  backdrop-filter: blur(14px);
}

.format-toolbar-enter-active,
.format-toolbar-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.format-toolbar-enter-from,
.format-toolbar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(16px);
}

.toolbar-button-group,
.toolbar-swatch-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.toolbar-button-group {
  padding-right: 10px;
  border-right: 1px solid #e1e1e1;
}

.toolbar-swatch-group.background {
  padding-left: 10px;
  border-left: 1px solid #e1e1e1;
}

.format-command,
.format-swatch {
  appearance: none;
  display: inline-grid;
  place-items: center;
  padding: 0;
  border: 1px solid #d8d8d8;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.format-command {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  font-family: "Noto Serif SC", "Songti SC", STSong, serif;
  font-size: 15px;
  font-weight: 900;
}

.format-command.italic {
  font-style: italic;
}

.format-command.underline {
  text-decoration: underline;
}

.format-swatch {
  width: 30px;
  height: 30px;
  border-radius: 999px;
}

.format-swatch::before {
  content: "";
  width: 20px;
  height: 20px;
  border: 1px solid rgba(15, 23, 42, 0.16);
  border-radius: 999px;
  background: var(--swatch-color);
}

.format-swatch.clear::before {
  background:
    linear-gradient(
      135deg,
      transparent 46%,
      rgba(15, 23, 42, 0.42) 47%,
      rgba(15, 23, 42, 0.42) 53%,
      transparent 54%
    ),
    #ffffff;
}

.format-command:hover,
.format-swatch:hover {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.format-command:active,
.format-swatch:active {
  transform: scale(var(--motion-press-scale));
}

.format-command.active,
.format-swatch.active {
  border-color: #111111;
  background: #f2f2f2;
  box-shadow:
    0 0 0 3px rgba(0, 0, 0, 0.08),
    inset 0 0 0 1px rgba(0, 0, 0, 0.08);
}

.format-command.active {
  color: #000000;
}
</style>
