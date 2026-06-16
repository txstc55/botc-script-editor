<script setup lang="ts">
import { ref } from "vue";
import CharacterPickerOverlay from "./components/CharacterPickerOverlay.vue";
import FabledPickerOverlay from "./components/FabledPickerOverlay.vue";
import ScriptPreview from "./components/ScriptPreview.vue";
import ScriptSidebar from "./components/ScriptSidebar.vue";
import TeamEditor from "./components/TeamEditor.vue";
import { useScriptEditor } from "./composables/useScriptEditor";
import type { FabledDraft, RoleDraft, TeamKey } from "./types";

const editor = useScriptEditor();
const fabledPickerOpen = ref(false);
const editingFabledId = ref<string | null>(null);
const editingFabled = ref<FabledDraft | null>(null);
const rolePickerOpen = ref(false);
const rolePickerTeam = ref<TeamKey>("townsfolk");
const editingRoleId = ref<string | null>(null);
const editingRole = ref<RoleDraft | null>(null);

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
</script>

<template>
  <main class="app-shell">
    <ScriptSidebar
      :script="editor.script"
      :import-error="editor.importError.value"
      @add-fabled="openFabledPicker"
      @edit-fabled="openFabledEditor"
      @remove-fabled="editor.removeFabled"
      @add-jinx="editor.addJinx"
      @remove-jinx="editor.removeJinx"
    />

    <ScriptPreview
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
</style>
