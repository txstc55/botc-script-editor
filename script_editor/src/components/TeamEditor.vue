<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { BookOpen, Plus, Trash2 } from "@lucide/vue";
import type { RoleDraft, ScriptDraft, TeamConfig, TeamKey } from "../types";

const props = defineProps<{
  script: ScriptDraft;
  selectedTeam: TeamKey;
  activeTeam: TeamConfig;
  teamOrder: TeamKey[];
}>();

const emit = defineEmits<{
  "update:selectedTeam": [team: TeamKey];
  "add-role": [team: TeamKey];
  "edit-role": [team: TeamKey, id: string];
  "remove-role": [team: TeamKey, id: string];
}>();

type DropPlacement = "before" | "after";

interface PendingRoleDrag {
  roleId: string;
  pointerId: number;
  startX: number;
  startY: number;
  offsetX: number;
  offsetY: number;
  width: number;
}

const DRAG_START_DISTANCE = 6;

const teamPanelTransition = ref("team-panel-forward");
const draggedRoleId = ref<string | null>(null);
const dropTargetRoleId = ref<string | null>(null);
const dropPlacement = ref<DropPlacement>("before");
const pendingRoleDrag = ref<PendingRoleDrag | null>(null);
const dragGhostX = ref(0);
const dragGhostY = ref(0);
const dragGhostWidth = ref(0);
const suppressClickAfterDrag = ref(false);
const isDraggingRole = computed(() => Boolean(draggedRoleId.value));
const draggedRole = computed(() =>
  props.activeTeam.roles.find((role) => role.id === draggedRoleId.value) ?? null,
);

watch(
  () => props.selectedTeam,
  (nextTeam, previousTeam) => {
    const nextIndex = props.teamOrder.indexOf(nextTeam);
    const previousIndex = props.teamOrder.indexOf(previousTeam);
    teamPanelTransition.value = nextIndex >= previousIndex ? "team-panel-forward" : "team-panel-backward";
    resetRoleDragState();
  },
);

function teamCount(script: ScriptDraft, team: TeamKey) {
  return script.teams[team].roles.filter((role) => role.selected).length;
}

function roleStateLabel(role: RoleDraft) {
  return role.selected ? "已加入" : "未加入";
}

function selectTeam(team: TeamKey) {
  if (team === props.selectedTeam) {
    return;
  }
  const currentIndex = props.teamOrder.indexOf(props.selectedTeam);
  const nextIndex = props.teamOrder.indexOf(team);
  teamPanelTransition.value = nextIndex >= currentIndex ? "team-panel-forward" : "team-panel-backward";
  emit("update:selectedTeam", team);
}

function editRole(role: RoleDraft) {
  if (suppressClickAfterDrag.value) {
    return;
  }
  emit("edit-role", props.activeTeam.key, role.id);
}

function startRolePointerDrag(role: RoleDraft, event: PointerEvent) {
  if (event.button !== 0 || isInteractiveDragTarget(event.target)) {
    return;
  }
  const cardRect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  pendingRoleDrag.value = {
    roleId: role.id,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    offsetX: event.clientX - cardRect.left,
    offsetY: event.clientY - cardRect.top,
    width: cardRect.width,
  };
  try {
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  } catch {
    // Some synthetic/webview events do not expose pointer capture.
  }
}

function moveRolePointerDrag(event: PointerEvent) {
  const pending = pendingRoleDrag.value;
  if (!pending || pending.pointerId !== event.pointerId) {
    return;
  }

  const movement = Math.hypot(event.clientX - pending.startX, event.clientY - pending.startY);
  if (!draggedRoleId.value && movement < DRAG_START_DISTANCE) {
    return;
  }

  event.preventDefault();
  if (!draggedRoleId.value) {
    draggedRoleId.value = pending.roleId;
    dragGhostWidth.value = pending.width;
    suppressClickAfterDrag.value = true;
  }
  updateDragGhostPosition(event.clientX, event.clientY, pending);
  updateDropTargetAtPoint(event.clientX, event.clientY);
}

function endRolePointerDrag(event: PointerEvent) {
  const pending = pendingRoleDrag.value;
  if (!pending || pending.pointerId !== event.pointerId) {
    return;
  }

  try {
    (event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId);
  } catch {
    // Pointer capture may already be released by the webview.
  }

  if (draggedRoleId.value && dropTargetRoleId.value) {
    reorderRole(draggedRoleId.value, dropTargetRoleId.value, dropPlacement.value);
  }
  const wasDragging = Boolean(draggedRoleId.value);
  resetRoleDragState();
  if (wasDragging) {
    window.setTimeout(() => {
      suppressClickAfterDrag.value = false;
    }, 120);
  }
}

function cancelRolePointerDrag() {
  resetRoleDragState();
  window.setTimeout(() => {
    suppressClickAfterDrag.value = false;
  }, 120);
}

function updateDropTargetAtPoint(clientX: number, clientY: number) {
  const targetCard = roleCardAtPoint(clientX, clientY);
  if (!targetCard) {
    dropTargetRoleId.value = null;
    return;
  }

  const targetId = targetCard.dataset.roleId;
  if (!targetId || targetId === draggedRoleId.value) {
    dropTargetRoleId.value = null;
    return;
  }

  const rect = targetCard.getBoundingClientRect();
  dropTargetRoleId.value = targetId;
  dropPlacement.value = clientY > rect.top + rect.height / 2 ? "after" : "before";
}

function updateDragGhostPosition(clientX: number, clientY: number, pending: PendingRoleDrag) {
  dragGhostX.value = clientX - pending.offsetX;
  dragGhostY.value = clientY - pending.offsetY;
}

function roleCardAtPoint(clientX: number, clientY: number) {
  const pointedCard = document
    .elementFromPoint(clientX, clientY)
    ?.closest<HTMLElement>(".role-editor-card");
  if (pointedCard) {
    return pointedCard;
  }

  const list = document.querySelector<HTMLElement>(".role-editor-list");
  if (!list) {
    return null;
  }
  const listRect = list.getBoundingClientRect();
  if (clientX < listRect.left || clientX > listRect.right || clientY < listRect.top || clientY > listRect.bottom) {
    return null;
  }

  const cards = Array.from(list.querySelectorAll<HTMLElement>(".role-editor-card"));
  if (!cards.length) {
    return null;
  }
  return cards.reduce((closest, card) => {
    const rect = card.getBoundingClientRect();
    const closestRect = closest.getBoundingClientRect();
    const cardDistance = Math.abs(clientY - (rect.top + rect.height / 2));
    const closestDistance = Math.abs(clientY - (closestRect.top + closestRect.height / 2));
    return cardDistance < closestDistance ? card : closest;
  }, cards[0]);
}

function reorderRole(draggedId: string, targetId: string, placement: DropPlacement) {
  const roles = props.activeTeam.roles;
  const fromIndex = roles.findIndex((role) => role.id === draggedId);
  if (fromIndex < 0) {
    return;
  }
  const [draggedRole] = roles.splice(fromIndex, 1);
  const targetIndex = roles.findIndex((role) => role.id === targetId);
  if (targetIndex < 0) {
    roles.splice(fromIndex, 0, draggedRole);
    return;
  }

  const insertionIndex = placement === "after" ? targetIndex + 1 : targetIndex;
  roles.splice(insertionIndex, 0, draggedRole);
}

function resetRoleDragState() {
  draggedRoleId.value = null;
  dropTargetRoleId.value = null;
  dropPlacement.value = "before";
  pendingRoleDrag.value = null;
  dragGhostX.value = 0;
  dragGhostY.value = 0;
  dragGhostWidth.value = 0;
}

function isInteractiveDragTarget(target: EventTarget | null) {
  return target instanceof Element && Boolean(target.closest("button, input, label, textarea, select"));
}
</script>

<template>
  <aside class="right-panel" aria-label="队伍编辑">
    <header class="pane-toolbar right-toolbar">
      <div class="toolbar-title">
        <BookOpen :size="18" aria-hidden="true" />
        <span>队伍</span>
      </div>
      <button class="icon-button" title="添加角色" type="button" @click="emit('add-role', props.selectedTeam)">
        <Plus :size="16" aria-hidden="true" />
      </button>
    </header>

    <nav class="team-tabs" aria-label="队伍标签">
      <button
        v-for="team in props.teamOrder"
        :key="team"
        class="team-tab"
        :class="{ active: props.selectedTeam === team }"
        :aria-label="`${props.script.teams[team].label}: ${teamCount(props.script, team)} 已加入`"
        type="button"
        @click="selectTeam(team)"
      >
        <span class="team-tab-label">{{ props.script.teams[team].label }}</span>
        <strong class="team-tab-count">{{ teamCount(props.script, team) }}</strong>
      </button>
    </nav>

    <Transition :name="teamPanelTransition" mode="out-in">
      <TransitionGroup
        :key="props.activeTeam.key"
        name="role-card-list"
        tag="div"
        class="role-editor-list team-editor"
        :class="{ dragging: isDraggingRole }"
      >
        <article
          v-for="role in props.activeTeam.roles"
          :key="role.id"
          class="role-editor-card"
          :class="{
            dragging: draggedRoleId === role.id,
            'drop-before': dropTargetRoleId === role.id && dropPlacement === 'before',
            'drop-after': dropTargetRoleId === role.id && dropPlacement === 'after',
          }"
          role="button"
          tabindex="0"
          :data-role-id="role.id"
          @click="editRole(role)"
          @keydown.enter="emit('edit-role', props.activeTeam.key, role.id)"
          @keydown.space.prevent="emit('edit-role', props.activeTeam.key, role.id)"
          @pointercancel="cancelRolePointerDrag"
          @pointerdown="startRolePointerDrag(role, $event)"
          @pointermove="moveRolePointerDrag"
          @pointerup="endRolePointerDrag"
        >
          <div class="role-card-head">
            <label class="check-label" @click.stop>
              <input v-model="role.selected" type="checkbox" />
              <span>{{ roleStateLabel(role) }}</span>
            </label>
            <img v-if="role.image" :alt="role.name" :src="role.image" class="role-card-image" />
            <span v-else class="role-card-fallback">{{ role.name.slice(0, 1) || "角" }}</span>
            <span class="role-card-name">{{ role.name }}</span>
            <div v-if="props.activeTeam.key !== 'traveler'" class="role-order-badges">
              <span v-if="role.firstNight" class="order-badge first-night">首夜</span>
              <span v-if="role.otherNight" class="order-badge other-night">其他</span>
            </div>
            <button
              class="ghost-icon"
              title="移除角色"
              type="button"
              @click.stop="emit('remove-role', props.activeTeam.key, role.id)"
            >
              <Trash2 :size="15" aria-hidden="true" />
            </button>
          </div>
          <p class="role-card-ability">{{ role.ability || "没有能力文本。" }}</p>
        </article>
      </TransitionGroup>
    </Transition>

    <Teleport to="body">
      <Transition name="role-drag-ghost">
        <article
          v-if="draggedRole"
          aria-hidden="true"
          class="role-editor-card role-drag-ghost-card"
          :style="{
            width: `${dragGhostWidth}px`,
            transform: `translate3d(${dragGhostX}px, ${dragGhostY}px, 0) rotate(0.7deg)`,
          }"
        >
          <div class="role-card-head">
            <label class="check-label">
              <input :checked="draggedRole.selected" tabindex="-1" type="checkbox" />
              <span>{{ roleStateLabel(draggedRole) }}</span>
            </label>
            <img v-if="draggedRole.image" :alt="draggedRole.name" :src="draggedRole.image" class="role-card-image" />
            <span v-else class="role-card-fallback">{{ draggedRole.name.slice(0, 1) || "角" }}</span>
            <span class="role-card-name">{{ draggedRole.name }}</span>
            <div v-if="props.activeTeam.key !== 'traveler'" class="role-order-badges">
              <span v-if="draggedRole.firstNight" class="order-badge first-night">首夜</span>
              <span v-if="draggedRole.otherNight" class="order-badge other-night">其他</span>
            </div>
            <span class="ghost-icon drag-ghost-remove-placeholder">
              <Trash2 :size="15" aria-hidden="true" />
            </span>
          </div>
          <p class="role-card-ability">{{ draggedRole.ability || "没有能力文本。" }}</p>
        </article>
      </Transition>
    </Teleport>
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
  position: relative;
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
  cursor: grab;
  outline: none;
  user-select: none;
  -webkit-user-select: none;
  transition:
    background var(--motion-duration-base) var(--motion-ease-standard),
    border-color var(--motion-duration-base) var(--motion-ease-standard),
    box-shadow var(--motion-duration-base) var(--motion-ease-standard),
    transform var(--motion-duration-base) var(--motion-ease-standard);
}

.role-editor-card:active,
.role-editor-list.dragging .role-editor-card {
  cursor: grabbing;
}

.role-editor-card:hover,
.role-editor-card:focus-visible {
  border-color: #111111;
  background: #fafafa;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-2px);
}

.role-editor-list.dragging .role-editor-card {
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    opacity var(--motion-duration-fast) var(--motion-ease-standard);
}

.role-editor-card.dragging {
  opacity: 0.42;
  transform: scale(0.98);
}

.role-editor-list.dragging .role-editor-card:hover,
.role-editor-list.dragging .role-editor-card:focus-visible {
  box-shadow: none;
  transform: none;
}

.role-editor-list.dragging .role-editor-card.dragging {
  transform: scale(0.98);
}

.role-editor-card.drop-before,
.role-editor-card.drop-after {
  border-color: #111111;
  background: #fafafa;
}

.role-editor-card.drop-before::before,
.role-editor-card.drop-after::after {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  height: 3px;
  border-radius: 999px;
  background: #111111;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
}

.role-editor-card.drop-before::before {
  top: -6px;
}

.role-editor-card.drop-after::after {
  bottom: -6px;
}

.role-drag-ghost-card {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 80;
  pointer-events: none;
  box-shadow:
    0 22px 55px rgba(0, 0, 0, 0.18),
    0 8px 22px rgba(0, 0, 0, 0.12);
  opacity: 0.96;
  transform-origin: 50% 50%;
  transition: none;
  will-change: transform;
}

.role-drag-ghost-card .check-label,
.role-drag-ghost-card .ghost-icon {
  pointer-events: none;
}

.drag-ghost-remove-placeholder {
  opacity: 0.35;
}

.role-drag-ghost-enter-active,
.role-drag-ghost-leave-active {
  transition:
    opacity var(--motion-duration-fast) var(--motion-ease-standard),
    filter var(--motion-duration-fast) var(--motion-ease-standard);
}

.role-drag-ghost-enter-from,
.role-drag-ghost-leave-to {
  opacity: 0;
  filter: blur(2px);
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

.team-panel-forward-enter-active,
.team-panel-forward-leave-active,
.team-panel-backward-enter-active,
.team-panel-backward-leave-active {
  transition:
    opacity var(--motion-duration-panel) var(--motion-ease-emphasized),
    transform var(--motion-duration-panel) var(--motion-ease-emphasized);
}

.team-panel-forward-enter-from,
.team-panel-backward-leave-to {
  opacity: 0;
  transform: translateX(22px);
}

.team-panel-forward-leave-to,
.team-panel-backward-enter-from {
  opacity: 0;
  transform: translateX(-22px);
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
