<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watchEffect } from "vue";
import CharacterPickerOverlay from "./components/CharacterPickerOverlay.vue";
import FabledPickerOverlay from "./components/FabledPickerOverlay.vue";
import JinxPickerOverlay from "./components/JinxPickerOverlay.vue";
import ScriptPreview from "./components/ScriptPreview.vue";
import ScriptSidebar from "./components/ScriptSidebar.vue";
import TeamEditor from "./components/TeamEditor.vue";
import { useScriptEditor } from "./composables/useScriptEditor";
import type { FabledDraft, JinxDraft, RoleDraft, TeamKey } from "./types";
import {
  isBatchExportMode,
  loadBatchExportJson,
  loadBatchExportManifest,
  saveBatchExportImage,
} from "./utils/batchExportClient";

interface ScriptPreviewExpose {
  renderPreviewImageDataUrl: (options?: {
    type?: "image/png" | "image/jpeg";
    quality?: number;
    backgroundColor?: string;
  }) => Promise<string>;
}

interface BatchExportFailure {
  relativePath: string;
  message: string;
}

const editor = useScriptEditor();
const fabledPickerOpen = ref(false);
const editingFabledId = ref<string | null>(null);
const editingFabled = ref<FabledDraft | null>(null);
const rolePickerOpen = ref(false);
const rolePickerTeam = ref<TeamKey>("townsfolk");
const editingRoleId = ref<string | null>(null);
const editingRole = ref<RoleDraft | null>(null);
const jinxPickerOpen = ref(false);
const editingJinxId = ref<string | null>(null);
const editingJinx = ref<JinxDraft | null>(null);
const previewRef = ref<ScriptPreviewExpose | null>(null);
const batchMode = isBatchExportMode();
const batchStatus = reactive({
  running: false,
  done: false,
  total: 0,
  completed: 0,
  failed: 0,
  current: "",
  root: "",
  output: "",
  error: "",
  failures: [] as BatchExportFailure[],
});
const batchProgressText = computed(() =>
  `${batchStatus.completed + batchStatus.failed} / ${batchStatus.total}`,
);

declare global {
  interface Window {
    __BOTC_BATCH_EXPORT_STATUS__?: {
      running: boolean;
      done: boolean;
      total: number;
      completed: number;
      failed: number;
      current: string;
      output: string;
      error: string;
      failures: BatchExportFailure[];
    };
  }
}

onMounted(() => {
  if (batchMode) {
    void startBatchExport();
  }
});

watchEffect(() => {
  if (!batchMode) {
    return;
  }

  window.__BOTC_BATCH_EXPORT_STATUS__ = {
    running: batchStatus.running,
    done: batchStatus.done,
    total: batchStatus.total,
    completed: batchStatus.completed,
    failed: batchStatus.failed,
    current: batchStatus.current,
    output: batchStatus.output,
    error: batchStatus.error,
    failures: [...batchStatus.failures],
  };
});

function openFabledPicker() {
  editingFabledId.value = null;
  editingFabled.value = null;
  fabledPickerOpen.value = true;
}

function openFabledEditor(id: string) {
  const role = editor.script.fabled.find((item) => item.id === id);
  if (!role) {
    return;
  }
  editingFabledId.value = id;
  editingFabled.value = { ...role };
  fabledPickerOpen.value = true;
}

function closeFabledPicker() {
  fabledPickerOpen.value = false;
  editingFabledId.value = null;
  editingFabled.value = null;
}

function handleFabledSubmit(role: FabledDraft) {
  if (editingFabledId.value) {
    editor.updateFabled(editingFabledId.value, role);
  } else {
    editor.addFabled(role);
  }
  closeFabledPicker();
}

function openRolePicker(team: TeamKey) {
  rolePickerTeam.value = team;
  editingRoleId.value = null;
  editingRole.value = null;
  rolePickerOpen.value = true;
}

function openRoleEditor(team: TeamKey, id: string) {
  const role = editor.script.teams[team].roles.find((item) => item.id === id);
  if (!role) {
    return;
  }
  rolePickerTeam.value = team;
  editingRoleId.value = id;
  editingRole.value = { ...role };
  rolePickerOpen.value = true;
}

function closeRolePicker() {
  rolePickerOpen.value = false;
  editingRoleId.value = null;
  editingRole.value = null;
}

function handleRoleSubmit(role: RoleDraft) {
  if (editingRoleId.value) {
    editor.updateRole(rolePickerTeam.value, editingRoleId.value, role);
  } else {
    editor.addRole(rolePickerTeam.value, role);
  }
  closeRolePicker();
}

function openJinxPicker() {
  editingJinxId.value = null;
  editingJinx.value = null;
  jinxPickerOpen.value = true;
}

function openJinxEditor(id: string) {
  const jinx = editor.script.jinxes.find((item) => item.id === id);
  if (!jinx) {
    return;
  }
  editingJinxId.value = id;
  editingJinx.value = { ...jinx, targets: [...jinx.targets] };
  jinxPickerOpen.value = true;
}

function closeJinxPicker() {
  jinxPickerOpen.value = false;
  editingJinxId.value = null;
  editingJinx.value = null;
}

function handleJinxSubmit(jinx: JinxDraft) {
  if (editingJinxId.value) {
    editor.updateJinx(editingJinxId.value, jinx);
  } else {
    editor.addJinx(jinx);
  }
  closeJinxPicker();
}

async function startBatchExport() {
  if (batchStatus.running) {
    return;
  }

  batchStatus.running = true;
  batchStatus.done = false;
  batchStatus.error = "";
  batchStatus.completed = 0;
  batchStatus.failed = 0;
  batchStatus.current = "";
  batchStatus.output = "";
  batchStatus.failures = [];

  try {
    const manifest = await loadBatchExportManifest();
    batchStatus.total = manifest.total;
    batchStatus.root = manifest.root;

    for (const item of manifest.files) {
      batchStatus.current = item.relativePath;
      try {
        const jsonText = await loadBatchExportJson(item.relativePath);
        await editor.loadPlayText(jsonText, item.fileName);
        await waitForPreviewRender();
        const dataUrl = await previewRef.value?.renderPreviewImageDataUrl({
          type: "image/jpeg",
          quality: 0.94,
          backgroundColor: "#ffffff",
        });
        if (!dataUrl) {
          throw new Error("预览还没有准备好。");
        }
        const saved = await saveBatchExportImage(item.relativePath, dataUrl);
        batchStatus.output = saved.outputRelativePath;
        batchStatus.completed += 1;
      } catch (error) {
        batchStatus.failed += 1;
        batchStatus.failures.push({
          relativePath: item.relativePath,
          message: error instanceof Error ? error.message : "导出失败",
        });
      }
    }
  } catch (error) {
    batchStatus.error = error instanceof Error ? error.message : "批量导出失败";
  } finally {
    batchStatus.running = false;
    batchStatus.done = true;
    batchStatus.current = "";
  }
}

async function waitForPreviewRender() {
  await nextTick();
  await document.fonts?.ready;
  await new Promise((resolve) => requestAnimationFrame(() => resolve(undefined)));
  await new Promise((resolve) => window.setTimeout(resolve, 80));
}
</script>

<template>
  <main class="app-shell">
    <ScriptSidebar
      :script="editor.script"
      :import-error="editor.importError.value"
      @add-fabled="openFabledPicker"
      @edit-fabled="openFabledEditor"
      @remove-fabled="editor.removeFabled"
      @add-jinx="openJinxPicker"
      @edit-jinx="openJinxEditor"
      @remove-jinx="editor.removeJinx"
    />

    <ScriptPreview
      ref="previewRef"
      :script="editor.script"
      :selected-role-count="editor.selectedRoleCount.value"
      @json-upload="editor.handleJsonUpload"
    />

    <TeamEditor
      :script="editor.script"
      :selected-team="editor.selectedTeam.value"
      :active-team="editor.activeTeam.value"
      :team-order="editor.teamOrder"
      @update:selected-team="editor.selectedTeam.value = $event"
      @add-role="openRolePicker"
      @edit-role="openRoleEditor"
      @remove-role="editor.removeRole"
      @set-role-selected="editor.setRoleSelected"
    />

    <FabledPickerOverlay
      :visible="fabledPickerOpen"
      :script-fabled="editingFabled"
      @close="closeFabledPicker"
      @add="handleFabledSubmit"
    />

    <CharacterPickerOverlay
      :visible="rolePickerOpen"
      :team="rolePickerTeam"
      :team-label="editor.script.teams[rolePickerTeam].label"
      :script-role="editingRole"
      @close="closeRolePicker"
      @submit="handleRoleSubmit"
    />

    <JinxPickerOverlay
      :visible="jinxPickerOpen"
      :script-jinx="editingJinx"
      :play-characters="editor.playCharacters.value"
      @close="closeJinxPicker"
      @submit="handleJinxSubmit"
    />

    <div v-if="batchMode" class="batch-export-overlay" aria-live="polite">
      <section class="batch-export-card">
        <div class="batch-export-kicker">批量导出</div>
        <h1>正在生成剧本图片</h1>
        <p>{{ batchProgressText }}</p>
        <progress :value="batchStatus.completed + batchStatus.failed" :max="Math.max(batchStatus.total, 1)" />
        <div class="batch-export-detail">
          <span v-if="batchStatus.current">当前：{{ batchStatus.current }}</span>
          <span v-else-if="batchStatus.done">完成：{{ batchStatus.completed }} 成功，{{ batchStatus.failed }} 失败</span>
          <span v-else>正在读取 all_jsons...</span>
        </div>
        <div v-if="batchStatus.output" class="batch-export-detail">最新输出：{{ batchStatus.output }}</div>
        <div v-if="batchStatus.error" class="batch-export-error">{{ batchStatus.error }}</div>
        <div v-if="batchStatus.failures.length" class="batch-export-errors">
          <div v-for="failure in batchStatus.failures.slice(-4)" :key="failure.relativePath">
            {{ failure.relativePath }}：{{ failure.message }}
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 320px minmax(430px, 1fr) 400px;
  height: 100vh;
  animation: app-shell-enter var(--motion-duration-panel) var(--motion-ease-emphasized) both;
  background:
    radial-gradient(circle at 1px 1px, rgba(0, 0, 0, 0.1) 1px, transparent 0) 0 0 / 22px 22px,
    #ffffff;
}

@keyframes app-shell-enter {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.995);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 300px minmax(420px, 1fr) 360px;
  }
}

.batch-export-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px);
  color: #111111;
}

.batch-export-card {
  width: min(560px, 100%);
  padding: 28px;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 80px rgba(17, 17, 17, 0.12);
}

.batch-export-kicker,
.batch-export-detail,
.batch-export-error,
.batch-export-errors {
  font-size: 13px;
  font-weight: 750;
}

.batch-export-kicker {
  color: rgba(17, 17, 17, 0.48);
}

.batch-export-card h1 {
  margin: 8px 0 0;
  font-size: 24px;
}

.batch-export-card p {
  margin: 14px 0 10px;
  font-size: 18px;
  font-weight: 850;
}

.batch-export-card progress {
  width: 100%;
  height: 10px;
  overflow: hidden;
  border: 0;
  border-radius: 999px;
  background: rgba(17, 17, 17, 0.08);
}

.batch-export-card progress::-webkit-progress-bar {
  background: rgba(17, 17, 17, 0.08);
}

.batch-export-card progress::-webkit-progress-value {
  border-radius: 999px;
  background: #111111;
}

.batch-export-detail {
  margin-top: 12px;
  color: rgba(17, 17, 17, 0.62);
  word-break: break-all;
}

.batch-export-error,
.batch-export-errors {
  margin-top: 12px;
  color: #8f1701;
  word-break: break-all;
}
</style>
