<script setup lang="ts">
import { Plus, Trash2 } from "@lucide/vue";
import type { ScriptNoteDraft } from "../types";

defineProps<{
  notes: ScriptNoteDraft[];
}>();

const emit = defineEmits<{
  add: [];
  remove: [id: string];
}>();

function updateNote(note: ScriptNoteDraft, event: Event) {
  note.text = (event.target as HTMLTextAreaElement).value;
  note.textHtml = undefined;
}
</script>

<template>
  <section class="notes-panel">
    <div class="notes-heading">
      <span>底部说明</span>
      <button class="notes-add" title="添加说明" type="button" @click="emit('add')">
        <Plus :size="16" aria-hidden="true" />
      </button>
    </div>

    <TransitionGroup name="note-list" tag="div" class="note-list">
      <article v-for="note in notes" :key="note.id" class="note-card">
        <textarea
          :value="note.text"
          aria-label="说明文字"
          placeholder="例如：中毒：中毒的玩家会失去能力……"
          rows="3"
          @input="updateNote(note, $event)"
        />
        <button class="note-remove" title="移除说明" type="button" @click="emit('remove', note.id)">
          <Trash2 :size="15" aria-hidden="true" />
        </button>
      </article>
    </TransitionGroup>

    <p v-if="!notes.length" class="notes-empty">说明会显示在传奇角色下方、剧本旅行者上方。</p>
  </section>
</template>

<style scoped>
.notes-panel {
  display: grid;
  gap: 10px;
  margin-bottom: 0;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  user-select: none;
  -webkit-user-select: none;
}

.notes-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  color: #111111;
  font-size: 13px;
  font-weight: 700;
}

.notes-add,
.note-remove {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 999px;
  cursor: pointer;
  transition:
    color var(--motion-duration-fast) var(--motion-ease-standard),
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.notes-add {
  border: 1px solid #111111;
  background: #ffffff;
  color: #111111;
}

.notes-add:hover,
.note-remove:hover {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
  transform: translateY(-1px);
}

.note-list {
  display: grid;
  gap: 8px;
}

.note-card {
  position: relative;
}

.note-card textarea {
  width: 100%;
  min-height: 72px;
  padding: 9px 38px 9px 10px;
  resize: vertical;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  background: #ffffff;
  color: #111111;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.5;
  outline: none;
  user-select: text;
  -webkit-user-select: text;
}

.note-card textarea:focus {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.note-remove {
  position: absolute;
  top: 6px;
  right: 5px;
  border: 1px solid transparent;
  background: transparent;
  color: #555555;
}

.notes-empty {
  margin: 0;
  color: #777777;
  font-size: 11px;
  font-weight: 650;
}

.note-list-move,
.note-list-enter-active,
.note-list-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.note-list-enter-from,
.note-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
