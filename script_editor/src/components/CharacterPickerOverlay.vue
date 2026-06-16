<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Check, ChevronLeft, Loader2, Plus, Save, Search, Trash2, X } from "@lucide/vue";
import type { RoleDraft, TeamKey } from "../types";
import VariantSelectControl from "./VariantSelectControl.vue";
import {
  characterRecordToDraft,
  deleteCharacterRecord,
  firstCharacterImage,
  firstVariant,
  loadCharacterEntryRecord,
  loadCharacterLibrary,
  mergeCharacterRecordVariants,
  normalizeCharacterRecord,
  saveCharacterRecord,
  type CharacterLibraryEntry,
  type CharacterLibrarySource,
  type CharacterRecord,
  type CharacterVariants,
} from "../utils/characterLibrary";

type OverlayMode = "list" | "editor";
type VariantField = keyof CharacterVariants;

interface CharacterForm {
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

const INITIAL_DATABASE_RENDER_COUNT = 80;
const DATABASE_RENDER_INCREMENT = 80;

const props = defineProps<{
  visible: boolean;
  team: TeamKey;
  teamLabel: string;
  scriptRole?: RoleDraft | null;
}>();

const emit = defineEmits<{
  close: [];
  submit: [role: RoleDraft];
}>();

const customEntries = ref<CharacterLibraryEntry[]>([]);
const databaseEntries = ref<CharacterLibraryEntry[]>([]);
const activeEntry = ref<CharacterLibraryEntry | null>(null);
const mode = ref<OverlayMode>("list");
const searchText = ref("");
const loading = ref(false);
const loadError = ref("");
const saveError = ref("");
const saveStatus = ref("");
const pendingDeleteName = ref("");
const databaseRenderLimit = ref(INITIAL_DATABASE_RENDER_COUNT);
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
const deletedVariantKeys = reactive<Record<VariantField, Set<string>>>({
  ability: new Set<string>(),
  image: new Set<string>(),
  firstNight: new Set<string>(),
  firstNightReminder: new Set<string>(),
  otherNight: new Set<string>(),
  otherNightReminder: new Set<string>(),
  reminders: new Set<string>(),
  remindersGlobal: new Set<string>(),
  setup: new Set<string>(),
  flavor: new Set<string>(),
});
const form = reactive<CharacterForm>({
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
const visibleDatabaseEntries = computed(() => filteredDatabaseEntries.value.slice(0, databaseRenderLimit.value));
const hiddenDatabaseCount = computed(() => filteredDatabaseEntries.value.length - visibleDatabaseEntries.value.length);
const hasMoreDatabaseEntries = computed(() => hiddenDatabaseCount.value > 0);
const activeRecord = computed(() => activeEntry.value?.record ?? null);
const editorTitle = computed(() => {
  if (activeRecord.value) {
    return `编辑：${activeRecord.value.name}`;
  }
  return props.scriptRole ? `编辑：${props.scriptRole.name}` : `创建自定义${props.teamLabel}角色`;
});
const editorSourceLabel = computed(() => {
  if (activeEntry.value?.source === "database") {
    return "来自已有数据库";
  }
  if (activeEntry.value?.source === "custom") {
    return "来自自定义数据库";
  }
  return props.scriptRole ? "来自当前剧本" : `新的自定义${props.teamLabel}角色`;
});

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      void openOverlay();
    }
  },
);

watch(
  () => props.team,
  () => {
    resetDatabaseRenderLimit();
    if (props.visible) {
      void openOverlay();
    }
  },
);

watch(searchText, () => {
  resetDatabaseRenderLimit();
});

async function openOverlay() {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  resetDatabaseRenderLimit();
  saveStatus.value = "";
  saveError.value = "";
  await refreshLibrary();
  if (props.scriptRole) {
    openScriptRoleEditor(props.scriptRole);
  } else {
    mode.value = "list";
  }
}

async function refreshLibrary() {
  loading.value = true;
  loadError.value = "";
  try {
    const library = await loadCharacterLibrary(props.team);
    customEntries.value = library.custom;
    databaseEntries.value = library.database;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "无法读取角色数据库。";
  } finally {
    loading.value = false;
  }
}

function filterEntries(entries: CharacterLibraryEntry[]) {
  const query = searchText.value.trim().toLowerCase();
  if (!query) {
    return entries;
  }
  return entries.filter((entry) => entry.record.name.toLowerCase().includes(query));
}

function resetDatabaseRenderLimit() {
  databaseRenderLimit.value = INITIAL_DATABASE_RENDER_COUNT;
}

function showMoreDatabaseEntries() {
  databaseRenderLimit.value += DATABASE_RENDER_INCREMENT;
}

function openBlankEditor() {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  resetVariantChoices();
  resetDeletedVariantKeys();
  Object.assign(form, {
    name: `新${props.teamLabel}角色`,
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

function openScriptRoleEditor(role: RoleDraft) {
  activeEntry.value = null;
  pendingDeleteName.value = "";
  resetVariantChoices();
  resetDeletedVariantKeys();
  fillFormFromRecord(draftToRecord(role));
  saveStatus.value = "";
  saveError.value = "";
  mode.value = "editor";
}

async function openEntryEditor(entry: CharacterLibraryEntry) {
  pendingDeleteName.value = "";
  saveStatus.value = "";
  saveError.value = "";
  loading.value = true;
  try {
    activeEntry.value = await loadCharacterEntryRecord(entry);
    resetVariantChoices();
    resetDeletedVariantKeys();
    fillFormFromRecord(activeEntry.value.record);
    mode.value = "editor";
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "无法读取角色资料。";
  } finally {
    loading.value = false;
  }
}

function draftToRecord(role: RoleDraft) {
  return normalizeCharacterRecord({
    id: role.name,
    name: role.name,
    team: props.team,
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
  }, props.team);
}

function fillFormFromRecord(record: CharacterRecord) {
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

function resetDeletedVariantKeys() {
  (Object.keys(deletedVariantKeys) as VariantField[]).forEach((field) => {
    deletedVariantKeys[field].clear();
  });
}

function variantOptions(field: VariantField) {
  const record = activeRecord.value;
  return record && activeEntry.value?.loaded ? record.variants[field] : [];
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
  const values = record && activeEntry.value?.loaded ? record.variants[field] : null;
  if (!values || values.length <= 1) {
    return;
  }

  const currentIndex = Math.min(Math.max(Number(variantChoice[field]) || 0, 0), values.length - 1);
  deletedVariantKeys[field].add(variantKey(values[currentIndex]));
  values.splice(currentIndex, 1);
  const nextIndex = Math.min(currentIndex, values.length - 1);
  variantChoice[field] = String(nextIndex);
  applyVariant(field, nextIndex);
  saveError.value = "";
  saveStatus.value = "已删除当前字段版本，保存后写入当前来源。";
}

async function saveCurrentCharacter() {
  saveStatus.value = "";
  saveError.value = "";
  try {
    const targetSource = activeEntry.value?.source ?? "custom";
    const saved = await saveCharacterRecord(props.team, targetSource, recordForSave(targetSource));
    upsertEntry(targetSource, saved);
    activeEntry.value = {
      source: targetSource,
      loaded: true,
      record: saved,
    };
    resetDeletedVariantKeys();
    saveStatus.value = targetSource === "database" ? `已保存到已有${props.teamLabel}数据库。` : `已保存到 custom/${props.teamLabel}。`;
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "保存失败。";
  }
}

async function deleteActiveCharacter() {
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
    await deleteCharacterRecord(activeEntry.value);
    if (activeEntry.value.source === "custom") {
      customEntries.value = customEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    } else {
      databaseEntries.value = databaseEntries.value.filter((entry) => entry.record.name !== activeEntry.value?.record.name);
    }
    activeEntry.value = null;
    pendingDeleteName.value = "";
    mode.value = "list";
    saveStatus.value = "已删除角色。";
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : "删除失败。";
  }
}

function submitCurrentCharacter() {
  emit("submit", characterRecordToDraft(formToRecord()));
  emit("close");
}

function recordForSave(targetSource: CharacterLibrarySource) {
  const currentRecord = formToRecord();
  const matchingCustomRecord = customEntries.value.find((entry) => entry.record.name === currentRecord.name)?.record;
  let merged = activeRecord.value ? mergeCharacterRecordVariants(activeRecord.value, currentRecord) : currentRecord;
  if (targetSource === "custom" && matchingCustomRecord && matchingCustomRecord !== activeRecord.value) {
    merged = mergeCharacterRecordVariants(matchingCustomRecord, merged);
  }
  return removeDeletedVariants(merged);
}

function formToRecord() {
  return normalizeCharacterRecord({
    id: form.name.trim(),
    name: form.name.trim() || `未命名${props.teamLabel}角色`,
    team: props.team,
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
  }, props.team);
}

function upsertEntry(source: CharacterLibrarySource, record: CharacterRecord) {
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
}

function parseTagText(value: string) {
  return value
    .split("||")
    .map((item) => item.trim())
    .filter(Boolean);
}

function removeDeletedVariants(record: CharacterRecord) {
  const normalized = normalizeCharacterRecord(record, props.team);
  normalized.variants.ability = filterDeletedVariantValues("ability", normalized.variants.ability);
  normalized.variants.image = filterDeletedVariantValues("image", normalized.variants.image);
  normalized.variants.firstNight = filterDeletedVariantValues("firstNight", normalized.variants.firstNight);
  normalized.variants.firstNightReminder = filterDeletedVariantValues(
    "firstNightReminder",
    normalized.variants.firstNightReminder,
  );
  normalized.variants.otherNight = filterDeletedVariantValues("otherNight", normalized.variants.otherNight);
  normalized.variants.otherNightReminder = filterDeletedVariantValues(
    "otherNightReminder",
    normalized.variants.otherNightReminder,
  );
  normalized.variants.reminders = filterDeletedVariantValues("reminders", normalized.variants.reminders);
  normalized.variants.remindersGlobal = filterDeletedVariantValues(
    "remindersGlobal",
    normalized.variants.remindersGlobal,
  );
  normalized.variants.setup = filterDeletedVariantValues("setup", normalized.variants.setup);
  normalized.variants.flavor = filterDeletedVariantValues("flavor", normalized.variants.flavor);
  return normalizeCharacterRecord(normalized, props.team);
}

function filterDeletedVariantValues<T>(field: VariantField, values: T[]) {
  const deletedKeys = deletedVariantKeys[field];
  if (!deletedKeys.size) {
    return values;
  }
  const remaining = values.filter((value) => !deletedKeys.has(variantKey(value)));
  return remaining.length ? remaining : values.slice(0, 1);
}

function variantKey(value: unknown) {
  return JSON.stringify(value);
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
    <Transition name="character-overlay">
      <div v-if="visible" class="overlay-shell" role="dialog" aria-modal="true" :aria-label="`选择${teamLabel}角色`">
        <button class="overlay-scrim" type="button" aria-label="关闭" @click="$emit('close')" />
        <section class="overlay-window">
          <Transition name="character-panel" mode="out-in">
            <div v-if="mode === 'list'" key="list" class="picker-panel">
              <header class="picker-header">
                <div class="search-wrap">
                  <Search :size="17" aria-hidden="true" />
                  <input v-model="searchText" class="search-input" :placeholder="`搜索${teamLabel}角色`" />
                </div>
                <button class="primary-icon" :title="`创建自定义${teamLabel}角色`" type="button" @click="openBlankEditor">
                  <Plus :size="18" aria-hidden="true" />
                </button>
                <button class="plain-icon" title="关闭" type="button" @click="$emit('close')">
                  <X :size="18" aria-hidden="true" />
                </button>
              </header>

              <div v-if="loading" class="loading-state">
                <Loader2 :size="22" aria-hidden="true" />
                <span>读取角色数据库...</span>
              </div>
              <p v-else-if="loadError" class="status-text error">{{ loadError }}</p>

              <div v-else class="library-scroll">
                <section class="library-section">
                  <h2>自定义{{ teamLabel }}角色</h2>
                  <div v-if="filteredCustomEntries.length" class="character-grid">
                    <button
                      v-for="entry in filteredCustomEntries"
                      :key="`custom-${entry.record.name}`"
                      class="character-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <img v-if="firstCharacterImage(entry.record)" :alt="entry.record.name" :src="firstCharacterImage(entry.record)" />
                      <span v-else class="image-fallback">{{ entry.record.name.slice(0, 1) }}</span>
                      <strong>{{ entry.record.name }}</strong>
                      <span class="occurrence-count">{{ entry.record.totalOccurrenceCount }}</span>
                      <span class="card-add">
                        <Plus :size="15" aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                  <p v-else class="empty-section">还没有自定义{{ teamLabel }}角色。</p>
                </section>

                <section class="library-section">
                  <h2>已有{{ teamLabel }}角色</h2>
                  <div class="character-grid">
                    <button
                      v-for="entry in visibleDatabaseEntries"
                      :key="`database-${entry.record.name}`"
                      class="character-card"
                      type="button"
                      @click="openEntryEditor(entry)"
                    >
                      <img v-if="firstCharacterImage(entry.record)" :alt="entry.record.name" :src="firstCharacterImage(entry.record)" />
                      <span v-else class="image-fallback">{{ entry.record.name.slice(0, 1) }}</span>
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
                    显示更多 {{ Math.min(hiddenDatabaseCount, DATABASE_RENDER_INCREMENT) }} 个
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
                    class="danger-action"
                    :class="{ armed: pendingDeleteName === activeEntry.record.name }"
                    type="button"
                    @click="deleteActiveCharacter"
                  >
                    <Trash2 :size="16" aria-hidden="true" />
                    <span>{{ pendingDeleteName === activeEntry.record.name ? "确认删除" : "删除" }}</span>
                  </button>
                  <button class="plain-action" title="保存" type="button" @click="saveCurrentCharacter">
                    <Save :size="16" aria-hidden="true" />
                    <span>保存</span>
                  </button>
                  <button class="confirm-action" title="加入剧本" type="button" @click="submitCurrentCharacter">
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
                      <span v-else>{{ form.name.slice(0, 1) || "角" }}</span>
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
                      <small>setup。为 1 时，表示开局设置时需要额外检查或调整。</small>
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

.load-more-button {
  justify-self: center;
  min-height: 38px;
  padding: 0 18px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font-size: 13px;
  font-weight: 850;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.load-more-button:hover {
  border-color: #111111;
  background: #f5f5f5;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.load-more-button:active {
  transform: scale(var(--motion-press-scale));
}

.character-card {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
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

.occurrence-count {
  color: #777777;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
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
}

.character-overlay-enter-active,
.character-overlay-leave-active,
.character-panel-enter-active,
.character-panel-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.character-overlay-enter-from,
.character-overlay-leave-to {
  opacity: 0;
}

.character-overlay-enter-from .overlay-window,
.character-overlay-leave-to .overlay-window {
  transform: translateY(18px) scale(0.975);
}

.character-overlay-enter-from .overlay-scrim,
.character-overlay-leave-to .overlay-scrim {
  background: rgba(0, 0, 0, 0);
  backdrop-filter: blur(0);
}

.character-panel-enter-from {
  opacity: 0;
  transform: translateX(22px) scale(0.99);
}

.character-panel-leave-to {
  opacity: 0;
  transform: translateX(-22px) scale(0.99);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
