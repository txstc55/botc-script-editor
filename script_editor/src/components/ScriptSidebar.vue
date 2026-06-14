<script setup lang="ts">
import { FileText, Link2, Plus, Trash2, Upload, WandSparkles } from "@lucide/vue";
import type { ScriptDraft } from "../types";

defineProps<{
  script: ScriptDraft;
  cleanupSummary: string;
  importError: string;
}>();

defineEmits<{
  "json-upload": [event: Event];
  "add-fabled": [];
  "remove-fabled": [id: string];
  "add-jinx": [];
  "remove-jinx": [id: string];
}>();
</script>

<template>
  <aside class="left-rail left-panel" aria-label="剧本控制">
    <section class="rail-row script-row">
      <div class="row-heading">
        <FileText :size="18" aria-hidden="true" />
        <span>剧本</span>
      </div>
      <label class="file-button">
        <Upload :size="16" aria-hidden="true" />
        <span>导入 JSON</span>
        <input accept=".json,application/json" type="file" @change="$emit('json-upload', $event)" />
      </label>
      <p class="import-status" :class="{ error: importError }">
        {{ importError || "" }}
      </p>
      <label class="field-label">
        <span>名称</span>
        <input v-model="script.name" class="text-field" />
      </label>
      <label class="field-label">
        <span>作者</span>
        <input v-model="script.author" class="text-field" />
      </label>
    </section>

    <section class="rail-row">
      <div class="row-heading with-action">
        <span class="heading-title">
          <WandSparkles :size="18" aria-hidden="true" />
          <span>传奇角色</span>
        </span>
        <button class="icon-button" title="添加传奇角色" type="button" @click="$emit('add-fabled')">
          <Plus :size="16" aria-hidden="true" />
        </button>
      </div>
      <div class="compact-list">
        <article v-for="role in script.fabled" :key="role.id" class="compact-item">
          <input v-model="role.name" class="inline-input role-name" />
          <textarea v-model="role.ability" class="compact-textarea" rows="2" />
          <button class="ghost-icon" title="移除传奇角色" type="button" @click="$emit('remove-fabled', role.id)">
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </article>
      </div>
    </section>

    <section class="rail-row">
      <div class="row-heading with-action">
        <span class="heading-title">
          <Link2 :size="18" aria-hidden="true" />
          <span>相克规则</span>
        </span>
        <button class="icon-button" title="添加相克规则" type="button" @click="$emit('add-jinx')">
          <Plus :size="16" aria-hidden="true" />
        </button>
      </div>
      <div class="compact-list">
        <article v-for="jinx in script.jinxes" :key="jinx.id" class="compact-item">
          <input v-model="jinx.name" class="inline-input role-name" />
          <textarea v-model="jinx.ability" class="compact-textarea" rows="3" />
          <button class="ghost-icon" title="移除相克规则" type="button" @click="$emit('remove-jinx', jinx.id)">
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </article>
      </div>
    </section>
  </aside>
</template>
