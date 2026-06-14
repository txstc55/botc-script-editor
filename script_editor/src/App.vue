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
      :cleanup-summary="editor.cleanupSummary.value"
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
