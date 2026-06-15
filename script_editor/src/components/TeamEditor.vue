<script setup lang="ts">
import { BookOpen, Plus, Trash2 } from "@lucide/vue";
import type { RoleDraft, ScriptDraft, TeamConfig, TeamKey } from "../types";

defineProps<{
  script: ScriptDraft;
  selectedTeam: TeamKey;
  activeTeam: TeamConfig;
  teamOrder: TeamKey[];
}>();

defineEmits<{
  "update:selectedTeam": [team: TeamKey];
  "add-role": [team: TeamKey];
  "remove-role": [team: TeamKey, id: string];
}>();

function teamCount(script: ScriptDraft, team: TeamKey) {
  return script.teams[team].roles.filter((role) => role.selected).length;
}

function roleStateLabel(role: RoleDraft) {
  return role.selected ? "已加入" : "候选";
}
</script>

<template>
  <aside class="right-panel" aria-label="队伍编辑">
    <header class="pane-toolbar right-toolbar">
      <div class="toolbar-title">
        <BookOpen :size="18" aria-hidden="true" />
        <span>队伍</span>
      </div>
      <button class="icon-button" title="添加角色" type="button" @click="$emit('add-role', selectedTeam)">
        <Plus :size="16" aria-hidden="true" />
      </button>
    </header>

    <nav class="team-tabs" aria-label="队伍标签">
      <button
        v-for="team in teamOrder"
        :key="team"
        class="team-tab"
        :class="{ active: selectedTeam === team }"
        :aria-label="`${script.teams[team].label}: ${teamCount(script, team)} 已加入`"
        type="button"
        @click="$emit('update:selectedTeam', team)"
      >
        <span class="team-tab-label">{{ script.teams[team].label }}</span>
        <strong class="team-tab-count">{{ teamCount(script, team) }}</strong>
      </button>
    </nav>

    <div class="role-editor-list team-editor">
      <article v-for="role in activeTeam.roles" :key="role.id" class="role-editor-row">
        <div class="role-editor-top">
          <label class="check-label">
            <input v-model="role.selected" type="checkbox" />
            <span>{{ roleStateLabel(role) }}</span>
          </label>
          <div v-if="activeTeam.key !== 'traveler'" class="role-order-badges">
            <span v-if="role.firstNight" class="order-badge first-night">首夜</span>
            <span v-if="role.otherNight" class="order-badge other-night">其他</span>
          </div>
          <button
            class="ghost-icon"
            title="移除角色"
            type="button"
            @click="$emit('remove-role', activeTeam.key, role.id)"
          >
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </div>
        <input v-model="role.name" class="inline-input role-name" />
        <textarea v-model="role.ability" class="ability-editor" rows="4" />
      </article>
    </div>
  </aside>
</template>

<style scoped>
.right-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-height: 0;
  border-left: 1px solid #d9e2ef;
  border-color: #d9e2ef;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
}

.pane-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid #d9e2ef;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
}

.right-toolbar {
  padding-right: 14px;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  color: #26313f;
  font-size: 13px;
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

.team-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  padding: 12px;
  border-bottom: 1px solid #d9e2ef;
}

.team-tab {
  display: grid;
  place-items: center;
  gap: 2px;
  min-width: 0;
  height: 52px;
  padding: 5px;
  border: 1px solid #d9e2ef;
  border-radius: 7px;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
}

.team-tab-label {
  max-width: 100%;
  overflow: hidden;
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.team-tab-count {
  color: #0f172a;
  font-size: 16px;
}

.team-tab.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.role-editor-list {
  display: grid;
  align-content: start;
  gap: 9px;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  padding-right: 2px;
}

.role-editor-row {
  position: relative;
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid #dce2e8;
  border-radius: 8px;
  background: #ffffff;
}

.role-editor-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 30px;
}

.check-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.check-label input {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
}

.role-order-badges {
  display: flex;
  flex: 1;
  justify-content: flex-end;
  gap: 5px;
  min-width: 0;
}

.order-badge {
  min-width: 0;
  max-width: 76px;
  overflow: hidden;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-badge.first-night {
  background: #e0f2fe;
  color: #0369a1;
}

.order-badge.other-night {
  background: #ede9fe;
  color: #6d28d9;
}

.inline-input,
.ability-editor {
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

.inline-input {
  height: 34px;
  padding: 0 10px;
}

.ability-editor {
  resize: none;
  padding: 8px 10px;
}

.inline-input:focus,
.ability-editor:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.role-name {
  font-weight: 700;
}
</style>
