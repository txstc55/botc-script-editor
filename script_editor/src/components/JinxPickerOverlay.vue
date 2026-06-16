<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Check, ChevronLeft, Loader2, Plus, Save, Search, Trash2, X } from "@lucide/vue";
import type { JinxDraft, PlayCharacterSummary } from "../types";
import VariantSelectControl from "./VariantSelectControl.vue";
import {
  deleteJinxRecord,
  draftToJinxRecord,
  firstVariant,
  jinxRecordMatchesPlay,
  jinxRecordToDraft,
  loadJinxEntryRecord,
  loadJinxLibrary,
  mergeJinxRecordVariants,
  normalizeJinxRecord,
  saveJinxRecord,
  type JinxLibraryEntry,
  type JinxLibrarySource,
  type JinxRecord,
} from "../utils/jinxLibrary";

type OverlayMode = "list" | "editor";

interface JinxForm {
  name: string;
  ability: string;
  targets: string[];
}

const INITIAL_DATABASE_RENDER_COUNT = 90;
const DATABASE_RENDER_INCREMENT = 90;

const props = defineProps<{
  visible: boolean;
  scriptJinx?: JinxDraft | null;
  playCharacters: PlayCharacterSummary[];
}>();

const emit = defineEmits<{
  close: [];
  submit: [jinx: JinxDraft];
}>();

const customEntries = ref<JinxLibraryEntry[]>([]);
const databaseEntries = ref<JinxLibraryEntry[]>([]);
const activeEntry = ref<JinxLibraryEntry | null>(null);
const mode = ref<OverlayMode>("list");
const searchText = ref("");
const loading = ref(false);
const loadError = ref("");
const formError = ref("");
const saveStatus = ref("");
const databaseRenderLimit = ref(INITIAL_DATABASE_RENDER_COUNT);
const abilityChoice = ref("0");
const pendingDeleteName = ref("");
const deletedAbilityVariantKeys = ref(new Set<string>());
const form = reactive<JinxForm>({
  name: "",
  ability: "",
  targets: [],
});

const currentPlayCharacterNames = computed(() => props.playCharacters.map((character) => character.name));
const filteredDatabaseEntries = computed(() => {
  return filterEntries(databaseEntries.value);
});
const filteredCustomEntries = computed(() => {
  return filterEntries(customEntries.value);
});
const visibleDatabaseEntries = computed(() => filteredDatabaseEntries.value.slice(0, databaseRenderLimit.value));
const hiddenDatabaseCount = computed(() => filteredDatabaseEntries.value.length - visibleDatabaseEntries.value.length);
const hasMoreDatabaseEntries = computed(() => hiddenDatabaseCount.value > 0);
const activeRecord = computed(() => activeEntry.value?.record ?? null);
const selectedTargetSet = computed(() => new Set(form.targets));
const displayImage = computed(() => imageForTargets(form.targets));
const editorTitle = computed(() => {
  if (activeRecord.value) {
    return `编辑：${activeRecord.value.name}`;
  }
  return props.scriptJinx ? `编辑：${props.scriptJinx.name}` : "创建相克规则";
});
const editorSourceLabel = computed(() => {
  if (activeEntry.value?.source === "custom") {
    return "来自自定义相克规则";
  }
  if (activeEntry.value?.source === "database") {
    return "来自相克规则数据库";
  }
  return props.scriptJinx ? "来自当前剧本" : "新的自定义相克规则";
});
const effectiveName = computed(() => form.targets.join("&"));
const canSubmit = computed(() => Boolean(form.targets.length && effectiveName.value && form.ability.trim()));

function filterEntries(entries: JinxLibraryEntry[]) {
  const playEntries = entries.filter((entry) => jinxRecordMatchesPlay(entry.record, currentPlayCharacterNames.value));
  const query = searchText.value.trim().toLowerCase();
  if (!query) {
    return playEntries;
  }
  return playEntries.filter((entry) => entry.record.name.toLowerCase().includes(query));
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      void openOverlay();
    }
  },
);

watch(searchText, () => {
  databaseRenderLimit.value = INITIAL_DATABASE_RENDER_COUNT;
});

async function openOverlay() {
  activeEntry.value = null;
  formError.value = "";
  saveStatus.value = "";
  pendingDeleteName.value = "";
  resetDeletedAbilityVariants();
  databaseRenderLimit.value = INITIAL_DATABASE_RENDER_COUNT;
  await refreshLibrary();
  if (props.scriptJinx) {
    openScriptJinxEditor(props.scriptJinx);
  } else {
    mode.value = "list";
  }
}

async function refreshLibrary() {
  loading.value = true;
  loadError.value = "";
  try {
    const library = await loadJinxLibrary();
    customEntries.value = library.custom;
    databaseEntries.value = library.database;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "无法读取相克规则数据库。";
  } finally {
    loading.value = false;
  }
}

function showMoreDatabaseEntries() {
  databaseRenderLimit.value += DATABASE_RENDER_INCREMENT;
}

function openBlankEditor() {
  activeEntry.value = null;
  abilityChoice.value = "0";
  pendingDeleteName.value = "";
  resetDeletedAbilityVariants();
  Object.assign(form, {
    name: "",
    ability: "",
    targets: [],
  });
  formError.value = "";
  saveStatus.value = "";
  mode.value = "editor";
}

function openScriptJinxEditor(jinx: JinxDraft) {
  activeEntry.value = null;
  abilityChoice.value = "0";
  pendingDeleteName.value = "";
  resetDeletedAbilityVariants();
  fillFormFromRecord(draftToJinxRecord(jinx));
  formError.value = "";
  saveStatus.value = "";
  mode.value = "editor";
}

async function openEntryEditor(entry: JinxLibraryEntry) {
  loading.value = true;
  formError.value = "";
  try {
    activeEntry.value = await loadJinxEntryRecord(entry);
    abilityChoice.value = "0";
    pendingDeleteName.value = "";
    resetDeletedAbilityVariants();
    fillFormFromRecord(activeEntry.value.record);
    saveStatus.value = "";
    mode.value = "editor";
  } catch (error) {
    formError.value = error instanceof Error ? error.message : "无法读取相克规则资料。";
  } finally {
    loading.value = false;
  }
}

function fillFormFromRecord(record: JinxRecord) {
  const targets = record.targets.filter((target) => props.playCharacters.some((character) => character.name === target));
  Object.assign(form, {
    name: targets.length ? targets.join("&") : record.name,
    ability: firstVariant(record.variants.ability, ""),
    targets,
  });
}

function toggleTarget(name: string) {
  const index = form.targets.indexOf(name);
  if (index >= 0) {
    form.targets.splice(index, 1);
  } else {
    form.targets.push(name);
  }
  syncNameAndDefaultImage();
}

function syncNameAndDefaultImage() {
  if (form.targets.length) {
    form.name = form.targets.join("&");
  } else {
    form.name = "";
  }
}

function imageForTargets(targets: string[]) {
  return targets
    .map((target) => props.playCharacters.find((character) => character.name === target))
    .find((character) => character?.image)?.image ?? "";
}

function abilityOptions() {
  return activeRecord.value?.variants.ability ?? [];
}

function applyAbilityVariant(selectedIndex: string | number) {
  const index = Number(selectedIndex);
  const options = abilityOptions();
  if (!Number.isInteger(index) || index < 0 || index >= options.length) {
    return;
  }
  abilityChoice.value = String(index);
  form.ability = options[index] ?? "";
}

function removeAbilityVariant() {
  const record = activeRecord.value;
  const values = record?.variants.ability;
  if (!values || values.length <= 1) {
    return;
  }
  const currentIndex = Math.min(Math.max(Number(abilityChoice.value) || 0, 0), values.length - 1);
  deletedAbilityVariantKeys.value.add(variantKey(values[currentIndex]));
  values.splice(currentIndex, 1);
  const nextIndex = Math.min(currentIndex, values.length - 1);
  abilityChoice.value = String(nextIndex);
  applyAbilityVariant(nextIndex);
  formError.value = "";
  saveStatus.value = "已删除当前描述版本，保存后写入当前来源。";
}

function submitCurrentJinx() {
  const record = formToRecord();
  if (!record) {
    return;
  }
  emit("submit", jinxRecordToDraft(record));
  emit("close");
}

async function saveCurrentJinx() {
  formError.value = "";
  saveStatus.value = "";
  try {
    const targetSource = activeEntry.value?.source ?? "custom";
    const record = await recordForSave(targetSource);
    if (!record) {
      return;
    }
    const saved = await saveJinxRecord(targetSource, record);
    upsertEntry(targetSource, saved);
    activeEntry.value = {
      source: targetSource,
      loaded: true,
      record: saved,
    };
    resetDeletedAbilityVariants();
    saveStatus.value = targetSource === "database" ? "已保存到已有相克规则数据库。" : "已保存到 custom/jinxes。";
  } catch (error) {
    formError.value = error instanceof Error ? error.message : "保存失败。";
  }
}

async function deleteActiveJinx() {
  if (!activeEntry.value) {
    return;
  }
  if (pendingDeleteName.value !== activeEntry.value.record.name) {
    pendingDeleteName.value = activeEntry.value.record.name;
    saveStatus.value = "";
    formError.value = `再次点击“确认删除”以删除「${activeEntry.value.record.name}」。`;
    return;
  }

  saveStatus.value = "";
  formError.value = "";
  try {
    await deleteJinxRecord(activeEntry.value);
    if (activeEntry.value.source === "custom") {
      customEntries.value = customEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    } else {
      databaseEntries.value = databaseEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    }
    activeEntry.value = null;
    pendingDeleteName.value = "";
    mode.value = "list";
  } catch (error) {
    formError.value = error instanceof Error ? error.message : "删除失败。";
  }
}

async function recordForSave(targetSource: JinxLibrarySource) {
  const currentRecord = formToRecord();
  if (!currentRecord) {
    return null;
  }

  let merged = activeRecord.value ? mergeJinxRecordVariants(activeRecord.value, currentRecord) : currentRecord;
  const matchingRecord = await loadedMatchingRecord(targetSource, currentRecord.name);
  if (matchingRecord && matchingRecord !== activeRecord.value) {
    merged = mergeJinxRecordVariants(matchingRecord, merged);
  }
  return removeDeletedAbilityVariants(merged);
}

function formToRecord() {
  const name = effectiveName.value;
  if (!form.targets.length || !name) {
    formError.value = "相克规则至少需要选择一个目标角色。";
    return null;
  }
  if (!form.ability.trim()) {
    formError.value = "相克规则描述不能为空。";
    return null;
  }

  return normalizeJinxRecord({
    id: name,
    name,
    team: "jinx",
    targets: form.targets,
    totalOccurrenceCount: activeRecord.value?.totalOccurrenceCount ?? 1,
    targetDetectionNotes: [],
    issueNotes: [],
    variants: {
      ability: [form.ability],
    },
  });
}

async function loadedMatchingRecord(source: JinxLibrarySource, name: string) {
  const entries = source === "custom" ? customEntries.value : databaseEntries.value;
  const existingEntry = entries.find((entry) => entry.record.name === name);
  if (!existingEntry) {
    return null;
  }

  const loadedEntry = await loadJinxEntryRecord(existingEntry);
  upsertEntry(source, loadedEntry.record);
  return loadedEntry.record;
}

function upsertEntry(source: JinxLibrarySource, record: JinxRecord) {
  const nextEntry = {
    source,
    loaded: true,
    record,
  };
  const entries = source === "custom" ? customEntries.value : databaseEntries.value;
  const existingIndex = entries.findIndex((entry) => entry.record.name === record.name);
  if (existingIndex >= 0) {
    entries.splice(existingIndex, 1, nextEntry);
  } else {
    entries.unshift(nextEntry);
  }
  if (source === "custom") {
    databaseEntries.value = databaseEntries.value.filter((entry) => entry.record.name !== record.name);
  }
}

function removeDeletedAbilityVariants(record: JinxRecord) {
  const normalized = normalizeJinxRecord(record);
  const deletedKeys = deletedAbilityVariantKeys.value;
  if (!deletedKeys.size) {
    return normalized;
  }

  const remaining = normalized.variants.ability.filter((value) => !deletedKeys.has(variantKey(value)));
  normalized.variants.ability = remaining.length ? remaining : normalized.variants.ability.slice(0, 1);
  return normalizeJinxRecord(normalized);
}

function resetDeletedAbilityVariants() {
  deletedAbilityVariantKeys.value = new Set<string>();
}

function variantKey(value: unknown) {
  return JSON.stringify(value);
}

function optionLabel(field: string, value: unknown, index: number) {
  const prefix = `版本 ${index + 1}`;
  return `${prefix} · ${truncate(String(value || "空"))}`;
}

function truncate(value: string) {
  return value.length > 34 ? `${value.slice(0, 34)}...` : value;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="jinx-overlay">
      <div v-if="visible" class="overlay-shell" role="dialog" aria-modal="true" aria-label="选择相克规则">
        <button class="overlay-scrim" type="button" aria-label="关闭" @click="$emit('close')" />
        <section class="overlay-window">
          <Transition name="jinx-panel" mode="out-in">
            <div v-if="mode === 'list'" key="list" class="picker-panel">
              <header class="picker-header">
                <div class="search-wrap">
                  <Search :size="17" aria-hidden="true" />
                  <input v-model="searchText" class="search-input" placeholder="搜索相克规则" />
                </div>
                <button class="primary-icon" title="创建自定义相克规则" type="button" @click="openBlankEditor">
                  <Plus :size="18" aria-hidden="true" />
                </button>
                <button class="plain-icon" title="关闭" type="button" @click="$emit('close')">
                  <X :size="18" aria-hidden="true" />
                </button>
              </header>

              <div v-if="loading" class="loading-state">
                <Loader2 :size="22" aria-hidden="true" />
                <span>读取相克规则数据库...</span>
              </div>
              <p v-else-if="loadError" class="status-text error">{{ loadError }}</p>

              <div v-else class="library-scroll">
                <section class="library-section">
                  <h2>自定义相克规则</h2>
                  <div v-if="filteredCustomEntries.length" class="jinx-grid">
                    <button
                      v-for="entry in filteredCustomEntries"
                      :key="`custom-${entry.record.name}`"
                      class="jinx-library-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <strong>{{ entry.record.name }}</strong>
                      <span class="occurrence-count">{{ entry.record.totalOccurrenceCount }}</span>
                      <span class="card-add">
                        <Plus :size="15" aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                  <p v-else class="empty-section">还没有自定义相克规则。</p>
                </section>

                <section class="library-section">
                  <h2>已有相克规则</h2>
                  <div class="jinx-grid">
                    <button
                      v-for="entry in visibleDatabaseEntries"
                      :key="entry.record.name"
                      class="jinx-library-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <strong>{{ entry.record.name }}</strong>
                      <span class="occurrence-count">{{ entry.record.totalOccurrenceCount }}</span>
                      <span class="card-add">
                        <Plus :size="15" aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                  <button
                    v-if="hasMoreDatabaseEntries"
                    class="load-more-button"
                    type="button"
                    @click="showMoreDatabaseEntries"
                  >
                    显示更多 {{ Math.min(hiddenDatabaseCount, DATABASE_RENDER_INCREMENT) }} 条
                  </button>
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
                    class="plain-action danger-action"
                    type="button"
                    @click="deleteActiveJinx"
                  >
                    <Trash2 :size="16" aria-hidden="true" />
                    <span>{{ pendingDeleteName === activeEntry.record.name ? "确认删除" : "删除" }}</span>
                  </button>
                  <button class="plain-action" title="保存相克规则" type="button" :disabled="!canSubmit" @click="saveCurrentJinx">
                    <Save :size="16" aria-hidden="true" />
                    <span>保存</span>
                  </button>
                  <button class="confirm-action" title="加入剧本" type="button" :disabled="!canSubmit" @click="submitCurrentJinx">
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
                        <small>由目标角色自动生成，至少需要选择一个目标。</small>
                        <input
                          :value="effectiveName || '请选择目标角色'"
                          class="text-field"
                          disabled
                        />
                      </label>
                    </div>

                    <div class="image-preview">
                      <img v-if="displayImage" :alt="effectiveName || '相克规则'" :src="displayImage" />
                      <span v-else>{{ (effectiveName || "克").slice(0, 1) }}</span>
                    </div>
                  </div>

                  <section class="field-block">
                    <span>目标角色</span>
                    <small>目标来自当前剧本。至少选择一个；名字会按选择顺序生成。</small>
                    <div class="target-grid">
                      <button
                        v-for="character in props.playCharacters"
                        :key="character.id"
                        class="target-chip"
                        :class="{ selected: selectedTargetSet.has(character.name) }"
                        type="button"
                        @click="toggleTarget(character.name)"
                      >
                        <img v-if="character.image" :alt="character.name" :src="character.image" />
                        <span v-else class="target-fallback">{{ character.name.slice(0, 1) }}</span>
                        <strong>{{ character.name }}</strong>
                      </button>
                    </div>
                  </section>

                  <label class="field-block">
                    <span>描述</span>
                    <VariantSelectControl
                      v-if="abilityOptions().length > 1"
                      field="ability"
                      :values="abilityOptions()"
                      :selected="abilityChoice"
                      :option-label="optionLabel"
                      @change="applyAbilityVariant"
                      @remove="removeAbilityVariant"
                    />
                    <textarea v-model="form.ability" class="textarea-field ability-field" />
                  </label>
                </div>

                <p v-if="formError" class="status-text error">{{ formError }}</p>
                <p v-if="saveStatus" class="status-text success">{{ saveStatus }}</p>
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
}

.overlay-window {
  position: relative;
  width: min(1040px, calc(100vw - 56px));
  height: min(720px, calc(100vh - 56px));
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.14);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.18);
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
.plain-action,
.confirm-action {
  display: inline-grid;
  place-items: center;
  height: 38px;
  border-radius: 999px;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.primary-icon,
.plain-icon,
.confirm-action {
  width: 38px;
}

.plain-action {
  grid-auto-flow: column;
  gap: 7px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 850;
}

.primary-icon,
.confirm-action {
  border: 1px solid #111111;
  background: #111111;
  color: #ffffff;
}

.plain-action:disabled,
.confirm-action:disabled {
  border-color: #d8d8d8;
  background: #f4f4f4;
  color: #999999;
  cursor: not-allowed;
}

.plain-icon,
.plain-action {
  border: 1px solid #d8d8d8;
  background: #ffffff;
  color: #111111;
}

.primary-icon:hover,
.plain-icon:hover,
.plain-action:not(:disabled):hover,
.confirm-action:not(:disabled):hover {
  transform: translateY(-1px);
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
  gap: 12px;
}

.library-section h2 {
  margin: 0;
  color: #111111;
  font-size: 13px;
  font-weight: 850;
}

.empty-section {
  margin: 0;
  color: #777777;
  font-size: 12px;
  font-weight: 700;
}

.jinx-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.jinx-library-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 7px 8px;
  min-height: 52px;
  padding: 10px 42px 10px 12px;
  border: 1px solid #e1e1e1;
  border-radius: 8px;
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

.jinx-library-card:hover {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.jinx-library-card strong {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.occurrence-count {
  color: #777777;
  font-size: 12px;
  font-weight: 800;
}

.card-add {
  position: absolute;
  right: 10px;
  display: inline-grid;
  place-items: center;
  width: 25px;
  height: 25px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  opacity: 0;
  transform: translateX(4px);
  transition:
    opacity var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.jinx-library-card:hover .card-add {
  opacity: 1;
  transform: translateX(0);
}

.load-more-button {
  justify-self: center;
  min-height: 36px;
  padding: 0 16px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font-weight: 800;
}

.loading-state,
.status-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 110px;
  color: #555555;
  font-size: 13px;
  font-weight: 700;
}

.loading-state svg {
  animation: spin 1s linear infinite;
}

.status-text.error {
  color: #b42318;
}

.status-text.success {
  color: #147a3f;
}

.editor-title {
  display: grid;
  gap: 2px;
  min-width: 0;
  color: #111111;
  font-size: 14px;
  font-weight: 850;
}

.editor-title small {
  color: #777777;
  font-size: 12px;
  font-weight: 700;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.danger-action {
  border-color: #111111;
}

.editor-form {
  display: grid;
  gap: 16px;
}

.form-row {
  display: grid;
  gap: 14px;
}

.identity-row {
  grid-template-columns: minmax(0, 1fr) 220px;
  align-items: stretch;
}

.field-stack {
  display: grid;
  gap: 12px;
}

.field-block {
  display: grid;
  gap: 7px;
  color: #111111;
  font-size: 13px;
  font-weight: 800;
}

.field-block small {
  color: #707070;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.45;
}

.text-field,
.textarea-field {
  width: 100%;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  background: #ffffff;
  color: #111111;
  font-size: 14px;
  font-weight: 700;
  outline: none;
}

.text-field {
  height: 38px;
  padding: 0 11px;
}

.text-field:disabled {
  background: #f5f5f5;
  color: #555555;
}

.textarea-field {
  min-height: 160px;
  resize: vertical;
  padding: 10px 11px;
  line-height: 1.55;
}

.image-preview {
  display: grid;
  place-items: center;
  min-height: 150px;
  border: 1px dashed #cfd5df;
  border-radius: 10px;
  background: #fbfbfb;
}

.image-preview img {
  width: 82px;
  height: 82px;
  object-fit: contain;
}

.image-preview span {
  color: #111111;
  font-size: 24px;
  font-weight: 900;
}

.target-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.target-chip {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 6px 9px;
  border: 1px solid #e1e1e1;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  text-align: left;
}

.target-chip.selected {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
}

.target-chip img,
.target-fallback {
  width: 28px;
  height: 28px;
}

.target-chip img {
  object-fit: contain;
}

.target-fallback {
  display: inline-grid;
  place-items: center;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  font-size: 12px;
  font-weight: 900;
}

.target-chip strong {
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jinx-overlay-enter-active,
.jinx-overlay-leave-active,
.jinx-panel-enter-active,
.jinx-panel-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.jinx-overlay-enter-from,
.jinx-overlay-leave-to {
  opacity: 0;
}

.jinx-overlay-enter-from .overlay-window,
.jinx-overlay-leave-to .overlay-window {
  transform: translateY(10px) scale(0.98);
}

.jinx-panel-enter-from,
.jinx-panel-leave-to {
  opacity: 0;
  transform: translateX(14px);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
