<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Check, ChevronLeft, Loader2, Plus, Save, Search, Trash2, X } from "@lucide/vue";
import type { FabledDraft } from "../types";
import VariantSelectControl from "./VariantSelectControl.vue";
import {
  deleteFabledRecord,
  fabledRecordToDraft,
  firstFabledImage,
  firstVariant,
  loadFabledLibrary,
  mergeFabledRecordVariants,
  normalizeFabledRecord,
  saveCustomFabledRecord,
  type FabledLibraryEntry,
  type FabledRecord,
  type FabledVariants,
} from "../utils/fabledLibrary";

type OverlayMode = "list" | "editor";
type VariantField = keyof FabledVariants;

interface FabledForm {
  name: string;
  image: string;
  ability: string;
  firstNight: number;
  firstNightReminder: string;
  otherNight: number;
  otherNightReminder: string;
  remindersText: string;
  remindersGlobalText: string;
  setup: 0 | 1;
  flavor: string;
}

const props = defineProps<{
  visible: boolean;
  scriptFabled?: FabledDraft | null;
}>();

const emit = defineEmits<{
  close: [];
  add: [role: FabledDraft];
}>();

const customEntries = ref<FabledLibraryEntry[]>([]);
const databaseEntries = ref<FabledLibraryEntry[]>([]);
const activeEntry = ref<FabledLibraryEntry | null>(null);
const mode = ref<OverlayMode>("list");
const searchText = ref("");
const loading = ref(false);
const loadError = ref("");
const saveError = ref("");
const saveStatus = ref("");
const pendingDeleteName = ref("");
const variantChoice = reactive<Record<VariantField, string>>({
  ability: "0",
  image: "0",
  firstNight: "0",
  firstNightReminder: "0",
  otherNight: "0",
  otherNightReminder: "0",
  reminders: "0",
  remindersGlobal: "0",
  setup: "0",
  flavor: "0",
});
const form = reactive<FabledForm>({
  name: "",
  image: "",
  ability: "",
  firstNight: 0,
  firstNightReminder: "",
  otherNight: 0,
  otherNightReminder: "",
  remindersText: "",
  remindersGlobalText: "",
  setup: 0,
  flavor: "",
});

const filteredCustomEntries = computed(() => filterEntries(customEntries.value));
const filteredDatabaseEntries = computed(() => filterEntries(databaseEntries.value));
const activeRecord = computed(() => activeEntry.value?.record ?? null);
const editorTitle = computed(() => {
  if (activeRecord.value) {
    return `编辑：${activeRecord.value.name}`;
  }
  return props.scriptFabled ? `编辑：${props.scriptFabled.name}` : "创建自定义传奇角色";
});
const editorSourceLabel = computed(() => {
  if (activeEntry.value?.source === "database") {
    return "来自已有数据库";
  }
  if (activeEntry.value?.source === "custom") {
    return "来自自定义数据库";
  }
  return props.scriptFabled ? "来自当前剧本" : "新的自定义传奇角色";
});

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      openOverlay();
    }
  },
);

async function openOverlay() {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  saveStatus.value = "";
  saveError.value = "";
  await refreshLibrary();
  if (props.scriptFabled) {
    openScriptFabledEditor(props.scriptFabled);
  } else {
    mode.value = "list";
  }
}

async function refreshLibrary() {
  loading.value = true;
  loadError.value = "";
  try {
    const library = await loadFabledLibrary();
    customEntries.value = library.custom;
    databaseEntries.value = library.database;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "无法读取传奇角色数据库。";
  } finally {
    loading.value = false;
  }
}

function filterEntries(entries: FabledLibraryEntry[]) {
  const query = searchText.value.trim().toLowerCase();
  if (!query) {
    return entries;
  }
  return entries.filter((entry) => entry.record.name.toLowerCase().includes(query));
}

function openBlankEditor() {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  resetVariantChoices();
  Object.assign(form, {
    name: "新传奇角色",
    image: "",
    ability: "",
    firstNight: 0,
    firstNightReminder: "",
    otherNight: 0,
    otherNightReminder: "",
    remindersText: "",
    remindersGlobalText: "",
    setup: 0,
    flavor: "",
  });
  saveStatus.value = "";
  saveError.value = "";
  mode.value = "editor";
}

function openScriptFabledEditor(role: FabledDraft) {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  resetVariantChoices();
  fillFormFromRecord(draftToRecord(role));
  saveStatus.value = "";
  saveError.value = "";
  mode.value = "editor";
}

function openEntryEditor(entry: FabledLibraryEntry) {
  activeEntry.value = entry;
  pendingDeleteName.value = "";
  resetVariantChoices();
  fillFormFromRecord(entry.record);
  saveStatus.value = "";
  saveError.value = "";
  mode.value = "editor";
}

function draftToRecord(role: FabledDraft) {
  return normalizeFabledRecord({
    id: role.name,
    name: role.name,
    team: "fabled",
    totalOccurrenceCount: 1,
    notes: [],
    variants: {
      ability: [role.ability ?? ""],
      image: [role.image ?? ""],
      firstNight: [role.firstNight ?? 0],
      firstNightReminder: [role.firstNightReminder ?? ""],
      otherNight: [role.otherNight ?? 0],
      otherNightReminder: [role.otherNightReminder ?? ""],
      reminders: [role.reminders ?? []],
      remindersGlobal: [role.remindersGlobal ?? []],
      setup: [role.setup ?? 0],
      flavor: [role.flavor ?? ""],
    },
  });
}

function fillFormFromRecord(record: FabledRecord) {
  Object.assign(form, {
    name: record.name,
    image: firstVariant(record.variants.image, ""),
    ability: firstVariant(record.variants.ability, ""),
    firstNight: firstVariant(record.variants.firstNight, 0),
    firstNightReminder: firstVariant(record.variants.firstNightReminder, ""),
    otherNight: firstVariant(record.variants.otherNight, 0),
    otherNightReminder: firstVariant(record.variants.otherNightReminder, ""),
    remindersText: firstVariant(record.variants.reminders, []).join("||"),
    remindersGlobalText: firstVariant(record.variants.remindersGlobal, []).join("||"),
    setup: firstVariant(record.variants.setup, 0),
    flavor: firstVariant(record.variants.flavor, ""),
  });
}

function resetVariantChoices() {
  (Object.keys(variantChoice) as VariantField[]).forEach((field) => {
    variantChoice[field] = "0";
  });
}

function variantOptions(field: VariantField) {
  const record = activeRecord.value;
  return record ? record.variants[field] : [];
}

function applyVariant(field: VariantField, selectedIndex: string | number) {
  const index = Number(selectedIndex);
  const options = variantOptions(field);
  if (!Number.isInteger(index) || index < 0 || index >= options.length) {
    return;
  }

  variantChoice[field] = String(index);
  const value = options[index];
  if (field === "ability") {
    form.ability = String(value ?? "");
  } else if (field === "image") {
    form.image = String(value ?? "");
  } else if (field === "firstNight") {
    form.firstNight = Number(value) || 0;
  } else if (field === "firstNightReminder") {
    form.firstNightReminder = String(value ?? "");
  } else if (field === "otherNight") {
    form.otherNight = Number(value) || 0;
  } else if (field === "otherNightReminder") {
    form.otherNightReminder = String(value ?? "");
  } else if (field === "reminders") {
    form.remindersText = Array.isArray(value) ? value.join("||") : "";
  } else if (field === "remindersGlobal") {
    form.remindersGlobalText = Array.isArray(value) ? value.join("||") : "";
  } else if (field === "setup") {
    form.setup = Number(value) ? 1 : 0;
  } else if (field === "flavor") {
    form.flavor = String(value ?? "");
  }
}

function removeVariant(field: VariantField) {
  const record = activeRecord.value;
  const values = record ? record.variants[field] : null;
  if (!values || values.length <= 1) {
    return;
  }

  const currentIndex = Math.min(Math.max(Number(variantChoice[field]) || 0, 0), values.length - 1);
  values.splice(currentIndex, 1);
  const nextIndex = Math.min(currentIndex, values.length - 1);
  variantChoice[field] = String(nextIndex);
  applyVariant(field, nextIndex);
  saveError.value = "";
  saveStatus.value = "已删除当前字段版本，保存后写入自定义数据库。";
}

async function saveCurrentFabled() {
  saveStatus.value = "";
  saveError.value = "";
  try {
    const saved = await saveCustomFabledRecord(recordForSave());
    upsertCustomEntry(saved);
    activeEntry.value = {
      source: "custom",
      record: saved,
    };
    saveStatus.value = "已保存到 custom/fabled。";
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "保存失败。";
  }
}

async function deleteActiveFabled() {
  if (!activeEntry.value) {
    return;
  }
  if (pendingDeleteName.value !== activeEntry.value.record.name) {
    pendingDeleteName.value = activeEntry.value.record.name;
    saveStatus.value = "";
    saveError.value = `再次点击“确认删除”以删除「${activeEntry.value.record.name}」。`;
    return;
  }

  saveStatus.value = "";
  saveError.value = "";
  try {
    await deleteFabledRecord(activeEntry.value);
    if (activeEntry.value.source === "custom") {
      customEntries.value = customEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    } else {
      databaseEntries.value = databaseEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    }
    activeEntry.value = null;
    pendingDeleteName.value = "";
    mode.value = "list";
    saveStatus.value = "已删除传奇角色。";
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "删除失败。";
  }
}

function addCurrentFabled() {
  emit("add", fabledRecordToDraft(formToRecord()));
  emit("close");
}

function recordForSave() {
  const currentRecord = formToRecord();
  const matchingCustomRecord = customEntries.value.find((entry) => entry.record.name === currentRecord.name)?.record;
  let merged = activeRecord.value ? mergeFabledRecordVariants(activeRecord.value, currentRecord) : currentRecord;
  if (matchingCustomRecord && matchingCustomRecord !== activeRecord.value) {
    merged = mergeFabledRecordVariants(matchingCustomRecord, merged);
  }
  return merged;
}

function formToRecord() {
  return normalizeFabledRecord({
    id: form.name.trim(),
    name: form.name.trim() || "未命名传奇角色",
    team: "fabled",
    totalOccurrenceCount: activeRecord.value?.totalOccurrenceCount ?? 1,
    notes: [],
    variants: {
      ability: [form.ability],
      image: [form.image],
      firstNight: [Number(form.firstNight) || 0],
      firstNightReminder: [form.firstNightReminder],
      otherNight: [Number(form.otherNight) || 0],
      otherNightReminder: [form.otherNightReminder],
      reminders: [parseTagText(form.remindersText)],
      remindersGlobal: [parseTagText(form.remindersGlobalText)],
      setup: [form.setup],
      flavor: [form.flavor],
    },
  });
}

function upsertCustomEntry(record: FabledRecord) {
  const nextEntry = {
    source: "custom" as const,
    record,
  };
  const existingIndex = customEntries.value.findIndex((entry) => entry.record.name === record.name);
  if (existingIndex >= 0) {
    customEntries.value.splice(existingIndex, 1, nextEntry);
  } else {
    customEntries.value.unshift(nextEntry);
  }
}

function parseTagText(value: string) {
  return value
    .split("||")
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionLabel(field: string, value: unknown, index: number) {
  const prefix = `版本 ${index + 1}`;
  if (field === "setup") {
    return `${prefix} · ${Number(value) ? "需要设置" : "无需设置"}`;
  }
  if (Array.isArray(value)) {
    const joined = value.join("、") || "空";
    return `${prefix} · ${truncate(joined)}`;
  }
  return `${prefix} · ${truncate(String(value || "空"))}`;
}

function truncate(value: string) {
  return value.length > 28 ? `${value.slice(0, 28)}...` : value;
}

function showVariantSelector(field: VariantField) {
  return variantOptions(field).length > 1;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fabled-overlay">
      <div v-if="visible" class="overlay-shell" role="dialog" aria-modal="true" aria-label="选择传奇角色">
        <button class="overlay-scrim" type="button" aria-label="关闭" @click="$emit('close')" />
        <section class="overlay-window">
          <Transition name="fabled-panel" mode="out-in">
            <div v-if="mode === 'list'" key="list" class="picker-panel">
              <header class="picker-header">
                <div class="search-wrap">
                  <Search :size="17" aria-hidden="true" />
                  <input v-model="searchText" class="search-input" placeholder="搜索传奇角色" />
                </div>
                <button class="primary-icon" title="创建自定义传奇角色" type="button" @click="openBlankEditor">
                  <Plus :size="18" aria-hidden="true" />
                </button>
                <button class="plain-icon" title="关闭" type="button" @click="$emit('close')">
                  <X :size="18" aria-hidden="true" />
                </button>
              </header>

              <div v-if="loading" class="loading-state">
                <Loader2 :size="22" aria-hidden="true" />
                <span>读取传奇角色数据库...</span>
              </div>
              <p v-else-if="loadError" class="status-text error">{{ loadError }}</p>

              <div v-else class="library-scroll">
                <section class="library-section">
                  <h2>自定义传奇角色</h2>
                  <div v-if="filteredCustomEntries.length" class="character-grid">
                    <button
                      v-for="entry in filteredCustomEntries"
                      :key="`custom-${entry.record.name}`"
                      class="character-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <img v-if="firstFabledImage(entry.record)" :alt="entry.record.name" :src="firstFabledImage(entry.record)" />
                      <span v-else class="image-fallback">{{ entry.record.name.slice(0, 1) }}</span>
                      <strong>{{ entry.record.name }}</strong>
                      <span class="card-add">
                        <Plus :size="15" aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                  <p v-else class="empty-section">还没有自定义传奇角色。</p>
                </section>

                <section class="library-section">
                  <h2>已有传奇角色</h2>
                  <div class="character-grid">
                    <button
                      v-for="entry in filteredDatabaseEntries"
                      :key="`database-${entry.record.name}`"
                      class="character-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <img v-if="firstFabledImage(entry.record)" :alt="entry.record.name" :src="firstFabledImage(entry.record)" />
                      <span v-else class="image-fallback">{{ entry.record.name.slice(0, 1) }}</span>
                      <strong>{{ entry.record.name }}</strong>
                      <span class="card-add">
                        <Plus :size="15" aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                </section>
              </div>
            </div>

            <div v-else key="editor" class="editor-panel">
              <header class="editor-header">
                <button class="plain-icon" title="返回列表" type="button" @click="mode = 'list'">
                  <ChevronLeft :size="18" aria-hidden="true" />
                </button>
                <div class="editor-title">
                  <span>{{ editorTitle }}</span>
                  <small>{{ editorSourceLabel }}</small>
                </div>
                <div class="editor-actions">
                  <button
                    v-if="activeEntry"
                    class="danger-action"
                    :class="{ armed: pendingDeleteName === activeEntry.record.name }"
                    type="button"
                    @click="deleteActiveFabled"
                  >
                    <Trash2 :size="16" aria-hidden="true" />
                    <span>{{ pendingDeleteName === activeEntry.record.name ? "确认删除" : "删除" }}</span>
                  </button>
                  <button class="plain-action" type="button" @click="saveCurrentFabled">
                    <Save :size="16" aria-hidden="true" />
                    <span>保存</span>
                  </button>
                  <button class="confirm-action" title="加入剧本" type="button" @click="addCurrentFabled">
                    <Check :size="18" aria-hidden="true" />
                  </button>
                </div>
              </header>

              <div class="editor-scroll">
                <div class="editor-form">
                  <div class="form-row identity-row">
                    <div class="field-stack identity-fields">
                      <label class="field-block">
                        <span>名字</span>
                        <input v-model="form.name" class="text-field" />
                      </label>

                      <label class="field-block">
                        <span>图片来源</span>
                        <VariantSelectControl
                          v-if="showVariantSelector('image')"
                          field="image"
                          :values="variantOptions('image')"
                          :selected="variantChoice.image"
                          :option-label="optionLabel"
                          @change="applyVariant('image', $event)"
                          @remove="removeVariant('image')"
                        />
                        <input v-model="form.image" class="text-field" />
                      </label>
                    </div>

                    <div class="image-preview">
                      <img v-if="form.image" :alt="form.name" :src="form.image" />
                      <span v-else>{{ form.name.slice(0, 1) || "传" }}</span>
                    </div>
                  </div>

                  <label class="field-block">
                    <span>能力</span>
                    <VariantSelectControl
                      v-if="showVariantSelector('ability')"
                      field="ability"
                      :values="variantOptions('ability')"
                      :selected="variantChoice.ability"
                      :option-label="optionLabel"
                      @change="applyVariant('ability', $event)"
                      @remove="removeVariant('ability')"
                    />
                    <textarea v-model="form.ability" class="textarea-field ability-field" />
                  </label>

                  <div class="form-row two-column-row">
                    <label class="field-block">
                      <span>首夜顺序</span>
                      <VariantSelectControl
                        v-if="showVariantSelector('firstNight')"
                        field="firstNight"
                        :values="variantOptions('firstNight')"
                        :selected="variantChoice.firstNight"
                        :option-label="optionLabel"
                        @change="applyVariant('firstNight', $event)"
                        @remove="removeVariant('firstNight')"
                      />
                      <input v-model.number="form.firstNight" class="text-field" min="0" step="0.01" type="number" />
                    </label>

                    <label class="field-block">
                      <span>其他夜晚顺序</span>
                      <VariantSelectControl
                        v-if="showVariantSelector('otherNight')"
                        field="otherNight"
                        :values="variantOptions('otherNight')"
                        :selected="variantChoice.otherNight"
                        :option-label="optionLabel"
                        @change="applyVariant('otherNight', $event)"
                        @remove="removeVariant('otherNight')"
                      />
                      <input v-model.number="form.otherNight" class="text-field" min="0" step="0.01" type="number" />
                    </label>
                  </div>

                  <div class="form-row two-column-row">
                    <label class="field-block">
                      <span>首夜提醒</span>
                      <VariantSelectControl
                        v-if="showVariantSelector('firstNightReminder')"
                        field="firstNightReminder"
                        :values="variantOptions('firstNightReminder')"
                        :selected="variantChoice.firstNightReminder"
                        :option-label="optionLabel"
                        @change="applyVariant('firstNightReminder', $event)"
                        @remove="removeVariant('firstNightReminder')"
                      />
                      <textarea v-model="form.firstNightReminder" class="textarea-field small" />
                    </label>

                    <label class="field-block">
                      <span>其他夜晚提醒</span>
                      <VariantSelectControl
                        v-if="showVariantSelector('otherNightReminder')"
                        field="otherNightReminder"
                        :values="variantOptions('otherNightReminder')"
                        :selected="variantChoice.otherNightReminder"
                        :option-label="optionLabel"
                        @change="applyVariant('otherNightReminder', $event)"
                        @remove="removeVariant('otherNightReminder')"
                      />
                      <textarea v-model="form.otherNightReminder" class="textarea-field small" />
                    </label>
                  </div>

                  <div class="form-row tags-row">
                    <label class="field-block">
                      <span>标签</span>
                      <small>提醒标记。多个标签用 || 分隔，会显示在角色相关标记里。</small>
                      <VariantSelectControl
                        v-if="showVariantSelector('reminders')"
                        field="reminders"
                        :values="variantOptions('reminders')"
                        :selected="variantChoice.reminders"
                        :option-label="optionLabel"
                        @change="applyVariant('reminders', $event)"
                        @remove="removeVariant('reminders')"
                      />
                      <textarea v-model="form.remindersText" class="textarea-field small" />
                    </label>

                    <label class="field-block">
                      <span>全局标签</span>
                      <small>全局提醒标记。即使角色不在本剧本中，也可以作为全局标记出现。</small>
                      <VariantSelectControl
                        v-if="showVariantSelector('remindersGlobal')"
                        field="remindersGlobal"
                        :values="variantOptions('remindersGlobal')"
                        :selected="variantChoice.remindersGlobal"
                        :option-label="optionLabel"
                        @change="applyVariant('remindersGlobal', $event)"
                        @remove="removeVariant('remindersGlobal')"
                      />
                      <textarea v-model="form.remindersGlobalText" class="textarea-field small" />
                    </label>

                    <label class="field-block setup-field">
                      <span>设置</span>
                      <small>1 表示开局设置时需要额外检查或调整。</small>
                      <VariantSelectControl
                        v-if="showVariantSelector('setup')"
                        field="setup"
                        :values="variantOptions('setup')"
                        :selected="variantChoice.setup"
                        :option-label="optionLabel"
                        @change="applyVariant('setup', $event)"
                        @remove="removeVariant('setup')"
                      />
                      <select v-model.number="form.setup" class="text-field">
                        <option :value="0">0 · 无需设置</option>
                        <option :value="1">1 · 需要设置</option>
                      </select>
                    </label>
                  </div>

                  <label class="field-block">
                    <span>背景故事</span>
                    <small>flavor。只用于记录角色风味文本，不影响剧本规则。</small>
                    <VariantSelectControl
                      v-if="showVariantSelector('flavor')"
                      field="flavor"
                      :values="variantOptions('flavor')"
                      :selected="variantChoice.flavor"
                      :option-label="optionLabel"
                      @change="applyVariant('flavor', $event)"
                      @remove="removeVariant('flavor')"
                    />
                    <textarea v-model="form.flavor" class="textarea-field small" />
                  </label>
                </div>

                <p v-if="saveStatus" class="status-text success">{{ saveStatus }}</p>
                <p v-if="saveError" class="status-text error">{{ saveError }}</p>
              </div>
            </div>
          </Transition>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay-shell {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 28px;
}

.overlay-scrim {
  position: absolute;
  inset: 0;
  border: 0;
  background: rgba(0, 0, 0, 0.24);
  backdrop-filter: blur(10px);
  cursor: default;
  transition:
    background var(--motion-duration-panel) var(--motion-ease-emphasized),
    backdrop-filter var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.overlay-window {
  position: relative;
  width: min(1160px, calc(100vw - 56px));
  height: min(760px, calc(100vh - 56px));
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.14);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.18);
  transform-origin: center;
}

.picker-panel,
.editor-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}

.picker-header,
.editor-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e5e5;
  background: rgba(250, 250, 250, 0.92);
}

.editor-header {
  grid-template-columns: auto minmax(0, 1fr) auto;
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #555555;
  transition:
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.search-wrap:focus-within {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.search-input {
  min-width: 0;
  width: 100%;
  border: 0;
  background: transparent;
  color: #111111;
  font-size: 14px;
  font-weight: 700;
  outline: none;
}

.primary-icon,
.plain-icon,
.confirm-action {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 999px;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.primary-icon,
.confirm-action {
  border: 1px solid #111111;
  background: #111111;
  color: #ffffff;
}

.primary-icon:hover,
.confirm-action:hover {
  background: #000000;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.plain-icon {
  border: 1px solid #d8d8d8;
  background: #ffffff;
  color: #111111;
}

.plain-icon:hover {
  border-color: #111111;
  background: #f5f5f5;
  transform: translateY(-1px);
}

.primary-icon:active,
.plain-icon:active,
.confirm-action:active,
.plain-action:active,
.danger-action:active,
.character-card:active {
  transform: scale(var(--motion-press-scale));
}

.library-scroll,
.editor-scroll {
  min-height: 0;
  overflow: auto;
  padding: 16px;
  scrollbar-width: none;
}

.library-scroll::-webkit-scrollbar,
.editor-scroll::-webkit-scrollbar {
  display: none;
}

.library-section {
  display: grid;
  gap: 10px;
  margin-bottom: 22px;
}

.library-section h2 {
  margin: 0;
  color: #111111;
  font-size: 13px;
  font-weight: 900;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.character-card {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 9px 40px 9px 10px;
  border: 1px solid #e1e1e1;
  border-radius: 10px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  text-align: left;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    box-shadow var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.character-card:hover {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-2px);
}

.character-card img,
.image-fallback,
.image-preview img,
.image-preview span {
  width: 38px;
  height: 38px;
}

.character-card img,
.image-preview img {
  object-fit: contain;
}

.image-fallback,
.image-preview span {
  display: inline-grid;
  place-items: center;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  font-weight: 900;
}

.character-card strong {
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-add {
  position: absolute;
  top: 50%;
  right: 10px;
  display: inline-grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: #111111;
  color: #ffffff;
  opacity: 0;
  transform: translateY(-50%) scale(0.9);
  transition:
    opacity var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.character-card:hover .card-add {
  opacity: 1;
  transform: translateY(-50%) scale(1);
}

.empty-section,
.status-text {
  margin: 0;
  color: #666666;
  font-size: 13px;
  font-weight: 700;
}

.status-text.success {
  color: #111111;
}

.status-text.error {
  color: #a40000;
}

.loading-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 180px;
  color: #333333;
  font-weight: 750;
}

.loading-state svg {
  animation: spin 900ms linear infinite;
}

.editor-title {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.editor-title span {
  overflow: hidden;
  color: #111111;
  font-size: 15px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-title small {
  color: #666666;
  font-size: 11px;
  font-weight: 700;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plain-action {
  position: relative;
  display: inline-grid;
  place-items: center;
  height: 38px;
  width: 38px;
  padding: 0;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font-weight: 850;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.plain-action span {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.plain-action:hover {
  border-color: #111111;
  background: #f5f5f5;
  color: #111111;
  transform: translateY(-1px);
}

.danger-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  min-width: 38px;
  padding: 0 11px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font-weight: 850;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.danger-action:hover {
  border-color: #111111;
  background: #f5f5f5;
  transform: translateY(-1px);
}

.danger-action.armed {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
}

.danger-action.armed:hover {
  background: #000000;
}

.editor-form {
  display: grid;
  gap: 18px;
  align-items: start;
  min-width: 0;
  padding-bottom: 10px;
}

.form-row {
  display: grid;
  gap: 16px;
  align-items: start;
  min-width: 0;
}

.identity-row {
  grid-template-columns: minmax(0, 1fr) 190px;
}

.field-stack {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.two-column-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tags-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 180px;
}

.field-block {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: #111111;
  font-size: 12px;
  font-weight: 850;
}

.field-block small {
  color: #666666;
  font-size: 11px;
  font-weight: 650;
  line-height: 1.45;
}

.text-field,
.textarea-field {
  width: 100%;
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

.text-field {
  height: 36px;
  padding: 0 10px;
}

.textarea-field {
  min-height: 82px;
  resize: vertical;
  padding: 9px 10px;
  line-height: 1.55;
}

.textarea-field.small {
  min-height: 66px;
}

.ability-field {
  min-height: 132px;
}

.text-field:focus,
.textarea-field:focus {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.image-preview {
  display: grid;
  place-items: center;
  align-self: stretch;
  min-height: 128px;
  border: 1px dashed #d8d8d8;
  border-radius: 10px;
  background: #fafafa;
  transition:
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    background var(--motion-duration-base) var(--motion-ease-standard);
}

.image-preview img,
.image-preview span {
  width: 58px;
  height: 58px;
}

@media (max-width: 820px) {
  .overlay-window {
    width: calc(100vw - 28px);
    height: calc(100vh - 28px);
  }

  .identity-row,
  .two-column-row,
  .tags-row {
    grid-template-columns: 1fr;
  }

  .image-preview {
    min-height: 108px;
  }
}

.fabled-overlay-enter-active,
.fabled-overlay-leave-active,
.fabled-panel-enter-active,
.fabled-panel-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.fabled-overlay-enter-from,
.fabled-overlay-leave-to {
  opacity: 0;
}

.fabled-overlay-enter-from .overlay-window,
.fabled-overlay-leave-to .overlay-window {
  transform: translateY(18px) scale(0.975);
}

.fabled-overlay-enter-from .overlay-scrim,
.fabled-overlay-leave-to .overlay-scrim {
  background: rgba(0, 0, 0, 0);
  backdrop-filter: blur(0);
}

.fabled-panel-enter-from {
  opacity: 0;
  transform: translateX(22px) scale(0.99);
}

.fabled-panel-leave-to {
  opacity: 0;
  transform: translateX(-22px) scale(0.99);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
