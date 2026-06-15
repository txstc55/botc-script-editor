<script setup lang="ts">
import ScriptPreview from "./components/ScriptPreview.vue";
import ScriptSidebar from "./components/ScriptSidebar.vue";
import TeamEditor from "./components/TeamEditor.vue";
import { useScriptEditor } from "./composables/useScriptEditor";

const editor = useScriptEditor();
</script>

<template>
  <main class="app-shell">
    <ScriptSidebar
      :script="editor.script"
      :import-error="editor.importError.value"
      @json-upload="editor.handleJsonUpload"
      @add-fabled="editor.addFabled"
      @remove-fabled="editor.removeFabled"
      @add-jinx="editor.addJinx"
      @remove-jinx="editor.removeJinx"
    />

    <ScriptPreview
      :script="editor.script"
      :selected-role-count="editor.selectedRoleCount.value"
    />

    <TeamEditor
      :script="editor.script"
      :selected-team="editor.selectedTeam.value"
      :active-team="editor.activeTeam.value"
      :team-order="editor.teamOrder"
      @update:selected-team="editor.selectedTeam.value = $event"
      @add-role="editor.addRole"
      @remove-role="editor.removeRole"
    />
  </main>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 320px minmax(430px, 1fr) 400px;
  height: 100vh;
  background:
    radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.12) 1px, transparent 0) 0 0 / 22px 22px,
    linear-gradient(135deg, rgba(14, 165, 233, 0.08), transparent 36%),
    #ffffff;
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 300px minmax(420px, 1fr) 360px;
    min-height: 720px;
  }
}
</style>
