<script setup lang="ts">
import { computed } from "vue";
import { FileText, ListOrdered, Plus, Trash2, Upload } from "@lucide/vue";
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
  "json-upload": [event: Event];
  "add-fabled": [];
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
      <div class="row-heading">
        <FileText :size="18" aria-hidden="true" />
        <span>剧本</span>
      </div>
      <label class="file-button">
        <Upload :size="16" aria-hidden="true" />
        <span>导入 JSON</span>
        <input accept=".json,application/json" type="file" @change="$emit('json-upload', $event)" />
      </label>
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
            <input
              :checked="props.script.builtInFirstNightEnabled[definition.id]"
              type="checkbox"
              @change="updateBuiltInFirstNightEnabled(definition.id, $event)"
            />
            <span>{{ definition.name }}</span>
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
      <div class="compact-list">
        <article v-for="role in props.script.fabled" :key="role.id" class="compact-item">
          <input v-model="role.name" class="inline-input role-name" />
          <textarea v-model="role.ability" class="compact-textarea" rows="2" />
          <button class="ghost-icon" title="移除传奇角色" type="button" @click="$emit('remove-fabled', role.id)">
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </article>
      </div>
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
      <div class="compact-list">
        <article v-for="jinx in props.script.jinxes" :key="jinx.id" class="compact-item">
          <input v-model="jinx.name" class="inline-input role-name" />
          <textarea v-model="jinx.ability" class="compact-textarea" rows="3" />
          <button class="ghost-icon" title="移除相克规则" type="button" @click="$emit('remove-jinx', jinx.id)">
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </article>
      </div>
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
  border-right: 1px solid #d9e2ef;
  border-color: #d9e2ef;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
}

.rail-row {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  gap: 10px;
  padding: 12px;
  overflow: hidden;
  border: 1px solid #dde7f2;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
}

.script-row {
  grid-template-rows: auto auto auto auto auto;
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
  color: #26313f;
  font-size: 13px;
  font-weight: 700;
}

.with-action {
  justify-content: space-between;
}

.field-label {
  display: grid;
  gap: 5px;
  color: #596579;
  font-size: 12px;
  font-weight: 650;
}

.file-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 36px;
  border: 1px solid #b8c5d8;
  border-radius: 7px;
  background: #edf4ff;
  color: #1d4ed8;
  cursor: pointer;
  font-size: 13px;
  font-weight: 750;
}

.file-button:hover {
  border-color: #2563eb;
  background: #dbeafe;
}

.file-button input {
  display: none;
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
  border: 1px solid #cfd6df;
  border-radius: 7px;
  background: #ffffff;
  color: #17202d;
  outline: none;
  transition:
    border-color 120ms ease,
    box-shadow 120ms ease;
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
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
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
  border: 1px solid #dce2e8;
  border-radius: 20px;
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
  border: 1px solid #bfd0e2;
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  font-size: 13px;
  font-weight: 900;
}

.night-order-name {
  min-width: 0;
  overflow: hidden;
  color: #26313f;
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
  color: #596579;
  font-size: 11px;
  font-weight: 800;
}

.night-order-editor.disabled {
  color: #94a3b8;
}

.night-order-editor-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.night-order-editor-toggle input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #2563eb;
}

.number-field:disabled {
  background: #f1f5f9;
  color: #94a3b8;
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
  border: 1px solid #dce2e8;
  border-radius: 8px;
  background: #f8fafc;
}

.role-name {
  font-weight: 700;
}

.icon-button,
.ghost-icon {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 7px;
  cursor: pointer;
}

.icon-button {
  border: 1px solid #b8c5d8;
  background: #edf4ff;
  color: #1d4ed8;
}

.icon-button:hover {
  border-color: #2563eb;
  background: #dbeafe;
}

.ghost-icon {
  border: 1px solid transparent;
  background: transparent;
  color: #64748b;
}

.ghost-icon:hover {
  border-color: #d9b8ae;
  background: #fff1ed;
  color: #b42318;
}

.compact-item > .ghost-icon {
  position: absolute;
  top: 9px;
  right: 8px;
}
</style>
