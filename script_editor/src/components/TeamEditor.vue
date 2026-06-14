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
