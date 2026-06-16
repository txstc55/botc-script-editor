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
  "edit-role": [team: TeamKey, id: string];
  "remove-role": [team: TeamKey, id: string];
}>();

function teamCount(script: ScriptDraft, team: TeamKey) {
  return script.teams[team].roles.filter((role) => role.selected).length;
}

function roleStateLabel(role: RoleDraft) {
  return role.selected ? "已加入" : "未加入";
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

    <TransitionGroup name="role-card-list" tag="div" class="role-editor-list team-editor">
      <article
        v-for="role in activeTeam.roles"
        :key="role.id"
        class="role-editor-card"
        role="button"
        tabindex="0"
        @click="$emit('edit-role', activeTeam.key, role.id)"
        @keydown.enter="$emit('edit-role', activeTeam.key, role.id)"
        @keydown.space.prevent="$emit('edit-role', activeTeam.key, role.id)"
      >
        <div class="role-card-head">
          <label class="check-label" @click.stop>
            <input v-model="role.selected" type="checkbox" />
            <span>{{ roleStateLabel(role) }}</span>
          </label>
          <img v-if="role.image" :alt="role.name" :src="role.image" class="role-card-image" />
          <span v-else class="role-card-fallback">{{ role.name.slice(0, 1) || "角" }}</span>
          <span class="role-card-name">{{ role.name }}</span>
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
        <p class="role-card-ability">{{ role.ability || "没有能力文本。" }}</p>
      </article>
    </TransitionGroup>
  </aside>
</template>

<style scoped>
.right-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-height: 0;
  border-left: 1px solid #e5e5e5;
  border-color: #e5e5e5;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(16px);
}

.pane-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid #e5e5e5;
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
  color: #111111;
  font-size: 13px;
  font-weight: 700;
}

.icon-button,
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
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.icon-button {
  border: 1px solid #111111;
  background: #ffffff;
  color: #111111;
}

.icon-button:hover {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.icon-button:active,
.ghost-icon:active,
.team-tab:active,
.role-editor-card:active {
  transform: scale(var(--motion-press-scale));
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

.team-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  padding: 12px;
  border-bottom: 1px solid #e5e5e5;
}

.team-tab {
  display: grid;
  place-items: center;
  gap: 2px;
  min-width: 0;
  height: 52px;
  padding: 5px;
  border: 1px solid #e1e1e1;
  border-radius: 8px;
  background: #ffffff;
  color: #555555;
  cursor: pointer;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    color var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.team-tab:hover {
  border-color: #111111;
  transform: translateY(-1px);
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
  color: #111111;
  font-size: 16px;
}

.team-tab.active {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
}

.team-tab.active .team-tab-count {
  color: #ffffff;
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

.role-editor-card {
  position: relative;
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

.role-editor-card:hover,
.role-editor-card:focus-visible {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-2px);
}

.role-card-head {
  display: grid;
  grid-template-columns: auto 32px minmax(0, 1fr) auto 30px;
  align-items: center;
  gap: 8px;
  min-height: 30px;
}

.check-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #555555;
  font-size: 12px;
  font-weight: 700;
}

.check-label input {
  width: 16px;
  height: 16px;
  accent-color: #111111;
}

.role-order-badges {
  display: flex;
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
  background: #eeeeee;
  color: #111111;
}

.order-badge.other-night {
  background: #f6f6f6;
  color: #333333;
}

.role-card-image,
.role-card-fallback {
  width: 32px;
  height: 32px;
}

.role-card-image {
  object-fit: contain;
}

.role-card-fallback {
  display: inline-grid;
  place-items: center;
  border: 1px solid #dedede;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  font-size: 13px;
  font-weight: 900;
}

.role-card-name {
  min-width: 0;
  overflow: hidden;
  color: #111111;
  font-size: 13px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-card-ability {
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

.role-card-list-move,
.role-card-list-enter-active,
.role-card-list-leave-active {
  transition:
    background var(--motion-duration-panel) var(--motion-ease-emphasized),
    border-color var(--motion-duration-panel) var(--motion-ease-emphasized),
    box-shadow var(--motion-duration-panel) var(--motion-ease-emphasized),
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.role-card-list-enter-from,
.role-card-list-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

.role-card-list-leave-active {
  position: absolute;
  width: calc(100% - 14px);
}

.inline-input,
.ability-editor {
  width: 100%;
  border: 1px solid #d8d8d8;
  border-radius: 8px;
  background: #ffffff;
  color: #111111;
  outline: none;
  transition:
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
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
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.role-name {
  font-weight: 700;
}
</style>
