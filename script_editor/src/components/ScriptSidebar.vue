<script setup lang="ts">
import { computed } from "vue";
import { FileText, ListOrdered, Plus, Trash2 } from "@lucide/vue";
import type { BuiltInFirstNightOrderKey, ScriptDraft } from "../types";
import {
  buildFirstNightOrderItems,
  builtInFirstNightOrderDefinitions,
  formatNightOrder,
} from "../utils/nightOrders";

const props = defineProps<{
  script: ScriptDraft;
  importError: string;
}>();

defineEmits<{
  "add-fabled": [];
  "edit-fabled": [id: string];
  "remove-fabled": [id: string];
  "add-jinx": [];
  "remove-jinx": [id: string];
}>();

const firstNightOrderItems = computed(() => buildFirstNightOrderItems(props.script));

function updateBuiltInFirstNightOrder(key: BuiltInFirstNightOrderKey, event: Event) {
  const input = event.target as HTMLInputElement;
  const value = Number(input.value);
  if (!Number.isFinite(value)) {
    return;
  }
  props.script.builtInFirstNightOrders[key] = value;
}

function updateBuiltInFirstNightEnabled(key: BuiltInFirstNightOrderKey, event: Event) {
  const input = event.target as HTMLInputElement;
  props.script.builtInFirstNightEnabled[key] = input.checked;
}
</script>

<template>
  <aside class="left-rail left-panel" aria-label="剧本控制">
    <section class="rail-row script-row">
      <p v-if="props.importError" class="import-status error">
        {{ props.importError }}
      </p>
      <label class="field-label">
        <span>名称</span>
        <input v-model="props.script.name" class="text-field" />
      </label>
      <label class="field-label">
        <span>作者</span>
        <input v-model="props.script.author" class="text-field" />
      </label>
    </section>

    <section class="rail-row night-order-row">
      <div class="row-heading">
        <ListOrdered :size="18" aria-hidden="true" />
        <span>首夜顺序</span>
      </div>

      <div class="night-order-list">
        <article v-for="item in firstNightOrderItems" :key="item.id" class="night-order-list-item">
          <img v-if="item.image" :alt="item.name" :src="item.image" class="night-order-image" />
          <span v-else class="night-order-fallback">{{ item.name.slice(0, 1) }}</span>
          <span class="night-order-name">{{ item.name }}</span>
          <span class="night-order-number">{{ formatNightOrder(item.order) }}</span>
        </article>
      </div>

      <div class="night-order-editors">
        <label
          v-for="definition in builtInFirstNightOrderDefinitions"
          :key="definition.id"
          :class="[
            'night-order-editor',
            { disabled: !props.script.builtInFirstNightEnabled[definition.id] },
          ]"
        >
          <span class="night-order-editor-toggle">
            <span>{{ definition.name }}</span>
            <input
              :checked="props.script.builtInFirstNightEnabled[definition.id]"
              type="checkbox"
              @change="updateBuiltInFirstNightEnabled(definition.id, $event)"
            />
          </span>
          <input
            :value="props.script.builtInFirstNightOrders[definition.id]"
            class="number-field"
            :disabled="!props.script.builtInFirstNightEnabled[definition.id]"
            min="0"
            step="0.01"
            type="number"
            @input="updateBuiltInFirstNightOrder(definition.id, $event)"
          />
        </label>
      </div>
    </section>

    <section class="rail-row">
      <div class="row-heading with-action">
        <span class="heading-title">
          <span>传奇角色</span>
        </span>
        <button class="icon-button" title="添加传奇角色" type="button" @click="$emit('add-fabled')">
          <Plus :size="16" aria-hidden="true" />
        </button>
      </div>
      <TransitionGroup name="sidebar-card-list" tag="div" class="compact-list fabled-list">
        <article
          v-for="role in props.script.fabled"
          :key="role.id"
          class="fabled-card"
          role="button"
          tabindex="0"
          @click="$emit('edit-fabled', role.id)"
          @keydown.enter="$emit('edit-fabled', role.id)"
          @keydown.space.prevent="$emit('edit-fabled', role.id)"
        >
          <div class="fabled-card-head">
            <img v-if="role.image" :alt="role.name" :src="role.image" class="fabled-card-image" />
            <span v-else class="fabled-card-fallback">{{ role.name.slice(0, 1) || "传" }}</span>
            <span class="fabled-card-name">{{ role.name }}</span>
            <button
              class="ghost-icon"
              title="移除传奇角色"
              type="button"
              @click.stop="$emit('remove-fabled', role.id)"
            >
              <Trash2 :size="15" aria-hidden="true" />
            </button>
          </div>
          <p class="fabled-card-ability">{{ role.ability || "没有能力文本。" }}</p>
        </article>
      </TransitionGroup>
    </section>

    <section class="rail-row">
      <div class="row-heading with-action">
        <span class="heading-title">
          <span>相克规则</span>
        </span>
        <button class="icon-button" title="添加相克规则" type="button" @click="$emit('add-jinx')">
          <Plus :size="16" aria-hidden="true" />
        </button>
      </div>
      <TransitionGroup name="sidebar-card-list" tag="div" class="compact-list">
        <article v-for="jinx in props.script.jinxes" :key="jinx.id" class="compact-item">
          <input v-model="jinx.name" class="inline-input role-name" />
          <textarea v-model="jinx.ability" class="compact-textarea" rows="3" />
          <button class="ghost-icon" title="移除相克规则" type="button" @click="$emit('remove-jinx', jinx.id)">
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </article>
      </TransitionGroup>
    </section>
  </aside>
</template>

<style scoped>
.left-rail {
  display: grid;
  grid-template-rows: auto minmax(210px, 0.95fr) minmax(150px, 0.75fr) minmax(190px, 1fr);
  gap: 12px;
  min-height: 0;
  padding: 14px;
  overflow: hidden;
  border-right: 1px solid #e5e5e5;
  border-color: #e5e5e5;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(16px);
}

.rail-row {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  gap: 10px;
  padding: 12px;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.script-row {
  grid-template-rows: auto auto auto auto;
  align-content: start;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
}

.script-row::-webkit-scrollbar {
  display: none;
}

.row-heading,
.heading-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  color: #111111;
  font-size: 13px;
  font-weight: 700;
}

.with-action {
  justify-content: space-between;
}

.field-label {
  display: grid;
  gap: 5px;
  color: #5f6368;
  font-size: 12px;
  font-weight: 650;
}

.import-status {
  min-height: 20px;
  margin: 0;
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.import-status.error {
  color: #b42318;
}

.text-field,
.inline-input,
.number-field,
.compact-textarea {
  width: 100%;
  border: 1px solid #d8d8d8;
  border-radius: 7px;
  background: #ffffff;
  color: #111111;
  outline: none;
  transition:
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.text-field,
.inline-input,
.number-field {
  height: 34px;
  padding: 0 10px;
}

.compact-textarea {
  resize: none;
  padding: 8px 10px;
}

.text-field:focus,
.inline-input:focus,
.number-field:focus,
.compact-textarea:focus {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.night-order-row {
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.night-order-list {
  display: grid;
  align-content: start;
  gap: 7px;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
  scrollbar-width: none;
}

.night-order-list::-webkit-scrollbar {
  display: none;
}

.night-order-list-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 5px 8px;
  border: 1px solid #e1e1e1;
  border-radius: 20px;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.night-order-list-item:hover {
  border-color: #111111;
  background: #fafafa;
  transform: translateY(-1px);
}

.night-order-image,
.night-order-fallback {
  width: 28px;
  height: 28px;
}

.night-order-image {
  object-fit: contain;
}

.night-order-fallback {
  display: inline-grid;
  place-items: center;
  border: 1px solid #dedede;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  font-size: 13px;
  font-weight: 900;
}

.night-order-name {
  min-width: 0;
  overflow: hidden;
  color: #111111;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.night-order-number {
  min-width: 42px;
  color: #0f172a;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  font-weight: 850;
  text-align: right;
}

.night-order-editors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding-top: 2px;
}

.night-order-editor {
  display: grid;
  gap: 5px;
  color: #555555;
  font-size: 11px;
  font-weight: 800;
}

.night-order-editor.disabled {
  color: #9a9a9a;
}

.night-order-editor-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.night-order-editor-toggle input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #111111;
}

.number-field:disabled {
  background: #f4f4f4;
  color: #9a9a9a;
  cursor: not-allowed;
}

.compact-list {
  display: grid;
  align-content: start;
  gap: 9px;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}

.compact-item {
  position: relative;
  display: grid;
  gap: 8px;
  padding: 10px;
  padding-right: 40px;
  border: 1px solid #e1e1e1;
  border-radius: 8px;
  background: #ffffff;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    box-shadow var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.compact-item:hover {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-2px);
}

.role-name {
  font-weight: 700;
}

.fabled-list {
  gap: 10px;
}

.fabled-card {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e1e1e1;
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
  outline: none;
  user-select: none;
  -webkit-user-select: none;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    box-shadow var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.fabled-card:hover,
.fabled-card:focus-visible {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-2px);
}

.fabled-card-head {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) 30px;
  align-items: center;
  gap: 8px;
}

.fabled-card-image,
.fabled-card-fallback {
  width: 32px;
  height: 32px;
}

.fabled-card-image {
  object-fit: contain;
}

.fabled-card-fallback {
  display: inline-grid;
  place-items: center;
  border: 1px solid #dedede;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  font-size: 13px;
  font-weight: 900;
}

.fabled-card-name {
  min-width: 0;
  overflow: hidden;
  color: #111111;
  font-size: 13px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fabled-card-ability {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #333333;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.icon-button {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.ghost-icon {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.icon-button {
  border: 1px solid #000000;
  background: #ffffff;
  color: #000000;
}

.icon-button:hover {
  border-color: #000000;
  background: #000000;
  color: #ffffff;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.ghost-icon {
  border: 1px solid transparent;
  background: transparent;
  color: #555555;
}

.ghost-icon:hover {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
  transform: translateY(-1px);
}

.icon-button:active,
.ghost-icon:active,
.fabled-card:active,
.compact-item:active {
  transform: scale(var(--motion-press-scale));
}

.sidebar-card-list-move,
.sidebar-card-list-enter-active,
.sidebar-card-list-leave-active {
  transition:
    background var(--motion-duration-panel) var(--motion-ease-emphasized),
    border-color var(--motion-duration-panel) var(--motion-ease-emphasized),
    box-shadow var(--motion-duration-panel) var(--motion-ease-emphasized),
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.sidebar-card-list-enter-from,
.sidebar-card-list-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

.sidebar-card-list-leave-active {
  position: absolute;
  width: calc(100% - 14px);
}

.compact-item > .ghost-icon {
  position: absolute;
  top: 9px;
  right: 8px;
}
</style>
