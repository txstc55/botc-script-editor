<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Eye, FileJson, ImageDown, Upload } from "@lucide/vue";
import type { ScriptDraft, TeamKey } from "../types";
import {
  buildFirstNightOrderItems,
  buildOtherNightOrderItems,
  formatNightOrder,
  type NightOrderBaseItem,
} from "../utils/nightOrders";
import { previewTeamOrder } from "../utils/playJson";
import TextFormatToolbar from "./preview/TextFormatToolbar.vue";
import {
  backgroundColorOptions,
  COLUMN_GAP,
  COLUMN_WIDTH,
  CONTENT_CENTER,
  CONTENT_RIGHT,
  CONTENT_WIDTH,
  CONTENT_X,
  DEFAULT_TEXT_COLOR,
  FIRST_SECTION_WITH_AUTHOR_Y,
  FIRST_SECTION_WITHOUT_AUTHOR_Y,
  HEADER_AUTHOR_Y,
  HEADER_TITLE_Y,
  LEFT_RAIL_X,
  MIN_CHARACTER_HIGHLIGHT_NAME_LENGTH,
  MIN_PREVIEW_HEIGHT,
  NIGHT_FALLBACK_FONT_SIZE,
  NIGHT_ICON_CENTER,
  NIGHT_ICON_FALLBACK_RADIUS,
  NIGHT_ICON_GAP,
  NIGHT_ICON_SIZE,
  NIGHT_ICON_START_Y,
  NIGHT_ICON_STEP,
  NIGHT_ICON_X,
  NIGHT_LABEL_FIRST_Y,
  NIGHT_LABEL_FONT_SIZE,
  NIGHT_LABEL_SECOND_Y,
  NIGHT_LABEL_X,
  NIGHT_RAIL_VERTICAL_MARGIN,
  PAGE_WIDTH,
  PAGE_X,
  PAGE_Y,
  RAIL_WIDTH,
  RIGHT_RAIL_X,
  ROLE_ABILITY_FONT_SIZE,
  ROLE_ABILITY_LINE_HEIGHT,
  ROLE_FALLBACK_FONT_SIZE,
  ROLE_ICON_GAP,
  ROLE_ICON_SIZE,
  ROLE_NAME_FONT_SIZE,
  ROLE_NAME_LINE_HEIGHT,
  ROLE_NAME_TO_ABILITY_GAP,
  ROLE_TEXT_WIDTH_PADDING,
  ROW_GAP,
  SCRIPT_AUTHOR_FONT_SIZE,
  SCRIPT_PAGE_BACKGROUND,
  SCRIPT_TITLE_FONT_SIZE,
  SECTION_BOTTOM_GAP,
  SECTION_HEADING_FONT_SIZE,
  SECTION_HEADING_LINE_GAP,
  SINGLE_COLUMN_WIDTH,
  SVG_WIDTH,
  TRANSPARENT_COLOR,
  emptyFormatState,
  teamColors,
  textColorOptions,
} from "./preview/previewConfig";
import type {
  AbilityHighlightRule,
  FormatState,
  NightOrderItem,
  PreviewRole,
  PreviewSection,
  PreviewSectionKey,
  SvgPreviewLayout,
  SvgRoleLayout,
  SvgSectionLayout,
  TextColorOption,
} from "./preview/previewTypes";
import { usePreviewPanZoom } from "./preview/usePreviewPanZoom";

const props = defineProps<{
  script: ScriptDraft;
  selectedRoleCount: number;
}>();

defineEmits<{
  "json-upload": [event: Event];
}>();

const previewSections = computed<PreviewSection[]>(() => {
  const roleSections = previewTeamOrder.map((team) => ({
    key: team,
    label: props.script.teams[team].label,
    roles: props.script.teams[team].roles.filter((role) => role.selected),
  }));
  const fabledSection: PreviewSection = {
    key: "fabled",
    label: "传奇角色",
    roles: props.script.fabled,
  };
  const travelerSection: PreviewSection = {
    key: "traveler",
    label: "剧本旅行者",
    roles: props.script.teams.traveler.roles.filter((role) => role.selected),
  };

  return [...roleSections, fabledSection, travelerSection].filter((section) => section.roles.length > 0);
});

const firstNightOrder = computed(() => withNightOrderColors(buildFirstNightOrderItems(props.script)));
const otherNightOrder = computed(() => withNightOrderColors(buildOtherNightOrderItems(props.script)));
const hasScriptAuthor = computed(() => props.script.author.trim().length > 0);
const firstSectionY = computed(() =>
  hasScriptAuthor.value ? FIRST_SECTION_WITH_AUTHOR_Y : FIRST_SECTION_WITHOUT_AUTHOR_Y,
);
const previewLayout = computed<SvgPreviewLayout>(() => buildPreviewLayout());
const currentPlayCharacterHighlightRules = computed(() => buildCurrentPlayCharacterHighlightRules());
const previewRoot = ref<HTMLElement | null>(null);
const toolbarVisible = ref(false);
const activeEditor = ref<HTMLElement | null>(null);
const savedSelectionSnapshot = ref<SelectionSnapshot | null>(null);
const toolbarFormatState = ref<FormatState>({ ...emptyFormatState });
const {
  previewStage,
  previewCanvasStyle,
  isPreviewPanning,
  handlePreviewWheel,
  handlePreviewPointerDown,
  handlePreviewPointerMove,
  handlePreviewPointerUp,
} = usePreviewPanZoom(previewLayout);

onMounted(() => {
  document.addEventListener("selectionchange", updateSelectionState);
});

onBeforeUnmount(() => {
  document.removeEventListener("selectionchange", updateSelectionState);
});

function withNightOrderColors(items: NightOrderBaseItem[]): NightOrderItem[] {
  return items.map((item) => ({
    ...item,
    color: teamColors[item.team],
  }));
}

function buildPreviewLayout(): SvgPreviewLayout {
  const sections = buildSections();
  const contentBottom = sections.length
    ? sections[sections.length - 1].y + sections[sections.length - 1].height
    : firstSectionY.value;
  const nightCenteringSections = sections.filter((section) => section.key !== "fabled" && section.key !== "traveler");
  const nightCenteringContentBottom = nightCenteringSections.length
    ? nightCenteringSections[nightCenteringSections.length - 1].y +
      nightCenteringSections[nightCenteringSections.length - 1].height
    : firstSectionY.value;
  const firstNightStackHeight = nightRailStackHeight(firstNightOrder.value.length);
  const otherNightStackHeight = nightRailStackHeight(otherNightOrder.value.length);
  const nightHeightForFirstCentered = Math.max(
    firstNightStackHeight + NIGHT_RAIL_VERTICAL_MARGIN * 2,
    otherNightStackHeight * 2 - firstNightStackHeight + NIGHT_RAIL_VERTICAL_MARGIN * 2,
  );
  const height = Math.max(MIN_PREVIEW_HEIGHT, contentBottom + 72, PAGE_Y * 2 + nightHeightForFirstCentered);
  const nightCenteringHeight = Math.max(
    MIN_PREVIEW_HEIGHT,
    nightCenteringContentBottom + 72,
    PAGE_Y * 2 + nightHeightForFirstCentered,
  );
  const pageHeight = height - PAGE_Y * 2;
  const nightCenteringPageHeight = nightCenteringHeight - PAGE_Y * 2;

  return {
    height,
    pageHeight,
    nightRailContentY: PAGE_Y + (nightCenteringPageHeight - firstNightStackHeight) / 2,
    sections,
    firstNightItems: firstNightOrder.value,
    otherNightItems: otherNightOrder.value,
  };
}

function nightRailStackHeight(orderCount: number) {
  const iconCount = Math.max(orderCount, 0);
  const iconStackHeight = iconCount > 0
    ? iconCount * NIGHT_ICON_SIZE + (iconCount - 1) * NIGHT_ICON_GAP
    : 0;
  return NIGHT_ICON_START_Y + iconStackHeight;
}

function buildSections(): SvgSectionLayout[] {
  const sections: SvgSectionLayout[] = [];
  let y = firstSectionY.value;

  for (const section of previewSections.value) {
    const color = teamColors[section.key];
    const heading = previewSectionHeading(section);
    const headingWidth = estimateTextWidth(heading, SECTION_HEADING_FONT_SIZE);
    const roleY = y + SECTION_HEADING_FONT_SIZE + SECTION_HEADING_LINE_GAP;
    let roles: SvgRoleLayout[];
    let tallestColumnHeight: number;

    if (section.roles.length === 1) {
      const centeredRoles = layoutColumn(section.roles, section.key, CONTENT_X, roleY, SINGLE_COLUMN_WIDTH, true);
      roles = centeredRoles.roles;
      tallestColumnHeight = centeredRoles.height;
    } else {
      const measuredRoles = section.roles.map((role) => layoutRole(role, section.key, CONTENT_X, roleY));
      const splitIndex = findColumnSplit(measuredRoles);
      const leftRoles = layoutColumn(section.roles.slice(0, splitIndex), section.key, CONTENT_X, roleY);
      const rightRoles = layoutColumn(
        section.roles.slice(splitIndex),
        section.key,
        CONTENT_X + COLUMN_WIDTH + COLUMN_GAP,
        roleY,
      );
      roles = [...leftRoles.roles, ...rightRoles.roles];
      tallestColumnHeight = Math.max(leftRoles.height, rightRoles.height);
    }
    const sectionHeight = Math.max(
      SECTION_HEADING_FONT_SIZE + SECTION_HEADING_LINE_GAP + 64,
      SECTION_HEADING_FONT_SIZE + SECTION_HEADING_LINE_GAP + tallestColumnHeight + SECTION_BOTTOM_GAP,
    );

    sections.push({
      key: section.key,
      heading,
      color,
      y,
      headingY: y + SECTION_HEADING_FONT_SIZE,
      lineX: Math.min(CONTENT_RIGHT - 80, CONTENT_X + headingWidth + 16),
      lineY: y + SECTION_HEADING_FONT_SIZE - 9,
      roles,
      height: sectionHeight,
    });

    y += sectionHeight;
  }

  return sections;
}

function layoutRole(
  role: PreviewRole,
  team: PreviewSectionKey,
  x: number,
  y: number,
  columnWidth = COLUMN_WIDTH,
  centerActualContent = false,
): SvgRoleLayout {
  const roleTextWidth = columnWidth - ROLE_ICON_SIZE - ROLE_ICON_GAP;
  const nameLines = wrapText(role.name, roleTextWidth, ROLE_NAME_FONT_SIZE);
  const abilityLines = wrapAbilityLines(role.ability, team, roleTextWidth, ROLE_ABILITY_FONT_SIZE);
  const actualTextWidth = centerActualContent
    ? measuredRoleTextWidth(nameLines, abilityLines, roleTextWidth)
    : roleTextWidth;
  const actualX = centerActualContent
    ? CONTENT_X + (CONTENT_WIDTH - (ROLE_ICON_SIZE + ROLE_ICON_GAP + actualTextWidth)) / 2
    : x;
  const textX = actualX + ROLE_ICON_SIZE + ROLE_ICON_GAP;
  const nameStartY = y + ROLE_NAME_FONT_SIZE;
  const abilityY = y + nameLines.length * ROLE_NAME_LINE_HEIGHT + ROLE_NAME_TO_ABILITY_GAP;
  const abilityHeight = Math.max(ROLE_ABILITY_LINE_HEIGHT, abilityLines.length * ROLE_ABILITY_LINE_HEIGHT + 4);
  const textHeight =
    nameLines.length * ROLE_NAME_LINE_HEIGHT +
    ROLE_NAME_TO_ABILITY_GAP +
    abilityLines.length * ROLE_ABILITY_LINE_HEIGHT;
  const height = Math.max(ROLE_ICON_SIZE + 10, textHeight + 8);

  return {
    id: role.id,
    role,
    team,
    color: teamColors[team],
    x: actualX,
    y,
    textX,
    imageX: actualX,
    imageY: y + 4,
    imageCenterX: actualX + ROLE_ICON_SIZE / 2,
    imageCenterY: y + 4 + ROLE_ICON_SIZE / 2,
    fallbackLetter: role.name.slice(0, 1),
    nameLines,
    abilityLines,
    nameStartY,
    abilityX: textX,
    abilityY,
    abilityWidth: actualTextWidth,
    abilityHeight,
    height,
  };
}

function layoutColumn(
  roles: PreviewRole[],
  team: PreviewSectionKey,
  x: number,
  startY: number,
  columnWidth = COLUMN_WIDTH,
  centerActualContent = false,
) {
  const layouts: SvgRoleLayout[] = [];
  let y = startY;

  for (const role of roles) {
    const layout = layoutRole(role, team, x, y, columnWidth, centerActualContent);
    layouts.push(layout);
    y += layout.height + ROW_GAP;
  }

  return {
    roles: layouts,
    height: columnHeight(layouts),
  };
}

function findColumnSplit(roles: SvgRoleLayout[]) {
  if (roles.length <= 1) {
    return roles.length;
  }

  let bestSplit = 1;
  let bestScore = Number.POSITIVE_INFINITY;

  for (let split = 1; split < roles.length; split += 1) {
    const leftHeight = columnHeight(roles.slice(0, split));
    const rightHeight = columnHeight(roles.slice(split));
    const score = Math.abs(leftHeight - rightHeight);
    if (score < bestScore) {
      bestScore = score;
      bestSplit = split;
    }
  }

  return bestSplit;
}

function columnHeight(roles: Pick<SvgRoleLayout, "height">[]) {
  if (!roles.length) {
    return 0;
  }
  return roles.reduce((height, role) => height + role.height, 0) + (roles.length - 1) * ROW_GAP;
}

function measuredRoleTextWidth(nameLines: string[], abilityLines: string[], maxWidth: number) {
  const nameWidth = Math.max(
    0,
    ...nameLines.map((line) => estimateTextWidth(line, ROLE_NAME_FONT_SIZE)),
  );
  const abilityWidth = Math.max(
    0,
    ...abilityLines.map((line) => estimateTextWidth(line, ROLE_ABILITY_FONT_SIZE)),
  );
  return Math.min(maxWidth, Math.max(nameWidth, abilityWidth) + ROLE_TEXT_WIDTH_PADDING);
}

function wrapText(value: string, maxWidth: number, fontSize: number): string[] {
  const text = value.replace(/\s+/g, " ").trim();
  if (!text) {
    return [""];
  }

  const maxUnits = Math.max(4, maxWidth / fontSize);
  const lines: string[] = [];
  let line = "";
  let width = 0;

  for (const char of text) {
    const charWidth = charWidthUnits(char);
    if (line && width + charWidth > maxUnits) {
      lines.push(line.trimEnd());
      line = char.trimStart();
      width = char.trim() ? charWidth : 0;
      continue;
    }
    line += char;
    width += charWidth;
  }

  if (line) {
    lines.push(line.trimEnd());
  }
  return lines;
}

function wrapAbilityLines(value: string, team: PreviewSectionKey, maxWidth: number, fontSize: number) {
  if (team !== "fabled") {
    return wrapText(value, maxWidth, fontSize);
  }
  return fabledAbilityDisplayText(value)
    .split("\n")
    .flatMap((line) => wrapText(line, maxWidth, fontSize));
}

function fabledAbilityDisplayText(value: string) {
  const sentences = value
    .split("。")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => `${part}。`);
  return sentences.length ? sentences.join("\n") : value;
}

function charWidthUnits(char: string) {
  if (/[\u3000-\u9fff\uff00-\uffef]/u.test(char)) {
    return 1;
  }
  if (/\s/u.test(char)) {
    return 0.34;
  }
  if (/[A-Z]/u.test(char)) {
    return 0.68;
  }
  if (/[a-z0-9]/u.test(char)) {
    return 0.56;
  }
  return 0.48;
}

function estimateTextWidth(value: string, fontSize: number) {
  return Array.from(value).reduce((width, char) => width + charWidthUnits(char) * fontSize, 0);
}

function previewSectionHeading(section: PreviewSection) {
  if (section.key === "fabled" || section.key === "traveler") {
    return section.label;
  }
  return `${teamSideLabel(section.key)} · ${section.label}`;
}

function teamSideLabel(team: TeamKey) {
  return team === "townsfolk" || team === "outsider" ? "善良阵营" : "邪恶阵营";
}

function roleAbilityHtml(role: PreviewRole, team: PreviewSectionKey) {
  const ability = abilityDisplayText(role.ability, team);
  if (role.abilityHtml && plainTextFromHtml(role.abilityHtml) === normalizeAbilityText(ability)) {
    return role.abilityHtml;
  }
  return highlightAbilityText(ability);
}

function abilityDisplayText(value: string, team: PreviewSectionKey) {
  return team === "fabled" ? fabledAbilityDisplayText(value) : value;
}

function highlightAbilityText(value: string) {
  const rules = abilityHighlightRules();
  let html = "";
  let index = 0;

  while (index < value.length) {
    const char = value[index];
    const bracketEnd = char === "[" ? value.indexOf("]", index + 1) : char === "【" ? value.indexOf("】", index + 1) : -1;
    if (bracketEnd >= 0) {
      html += `<span class="ability-bracket-highlight">${escapeHtml(value.slice(index, bracketEnd + 1))}</span>`;
      index = bracketEnd + 1;
      continue;
    }

    const matchedRule = rules.find((rule) => value.startsWith(rule.text, index));
    if (matchedRule) {
      html += `<span style="color: ${matchedRule.color}; font-weight: 900;">${escapeHtml(matchedRule.text)}</span>`;
      index += matchedRule.text.length;
      continue;
    }

    html += char === "\n" ? "<br>" : escapeHtml(char);
    index += 1;
  }

  return html;
}

function abilityHighlightRules() {
  const semanticRules: AbilityHighlightRule[] = [
    { text: "善良角色", color: teamColors.townsfolk, priority: 1 },
    { text: "善良玩家", color: teamColors.townsfolk, priority: 1 },
    { text: "善良", color: teamColors.townsfolk, priority: 1 },
    { text: "镇民角色", color: teamColors.townsfolk, priority: 1 },
    { text: "镇民", color: teamColors.townsfolk, priority: 1 },
    { text: "外来角色", color: teamColors.outsider, priority: 1 },
    { text: "外来者", color: teamColors.outsider, priority: 1 },
    { text: "外来", color: teamColors.outsider, priority: 1 },
    { text: "爪牙角色", color: teamColors.minion, priority: 1 },
    { text: "爪牙", color: teamColors.minion, priority: 1 },
    { text: "中毒", color: teamColors.minion, priority: 1 },
    { text: "醉酒", color: teamColors.minion, priority: 1 },
    { text: "邪恶角色", color: teamColors.minion, priority: 1 },
    { text: "邪恶玩家", color: teamColors.minion, priority: 1 },
    { text: "邪恶", color: teamColors.minion, priority: 1 },
    { text: "恶魔角色", color: teamColors.demon, priority: 1 },
    { text: "恶魔", color: teamColors.demon, priority: 1 },
    { text: "死亡", color: teamColors.demon, priority: 1 },
    { text: "处决", color: teamColors.demon, priority: 1 },
    { text: "疯狂", color: teamColors.traveler, priority: 1 },
  ];

  return [...currentPlayCharacterHighlightRules.value, ...semanticRules].sort(
    (left, right) =>
      right.text.length - left.text.length ||
      right.priority - left.priority ||
      left.text.localeCompare(right.text, "zh-Hans-CN"),
  );
}

function buildCurrentPlayCharacterHighlightRules() {
  const rulesByName = new Map<string, AbilityHighlightRule>();
  for (const team of Object.values(props.script.teams)) {
    for (const role of team.roles) {
      const name = role.name.trim();
      if (!role.selected || name.length < MIN_CHARACTER_HIGHLIGHT_NAME_LENGTH) {
        continue;
      }
      rulesByName.set(name, {
        text: name,
        color: teamColors[team.key],
        priority: 2,
      });
    }
  }

  for (const role of props.script.fabled) {
    const name = role.name.trim();
    if (name.length < MIN_CHARACTER_HIGHLIGHT_NAME_LENGTH) {
      continue;
    }
    rulesByName.set(name, {
      text: name,
      color: teamColors.fabled,
      priority: 2,
    });
  }

  return [...rulesByName.values()];
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function handleAbilityBlur(role: PreviewRole, event: FocusEvent) {
  if (isTextFormatToolbarTarget(event.relatedTarget)) {
    return;
  }
  saveAbilityEditor(role, event.currentTarget as HTMLElement);
}

function isTextFormatToolbarTarget(target: EventTarget | null) {
  return target instanceof Element && Boolean(target.closest(".text-format-toolbar"));
}

function saveAbilityEditor(role: PreviewRole, editor: HTMLElement) {
  role.abilityHtml = editor.innerHTML;
}

function plainTextFromHtml(html: string) {
  if (typeof document === "undefined") {
    return "";
  }
  const element = document.createElement("div");
  element.innerHTML = html;
  element.querySelectorAll("br").forEach((breakElement) => {
    breakElement.replaceWith(document.createTextNode("\n"));
  });
  return normalizeAbilityText(element.textContent ?? "");
}

function normalizeAbilityText(value: string) {
  return value.replace(/\u00a0/g, " ").replace(/\n+$/g, "");
}

function preventPreviewTextMutation(event: Event) {
  event.preventDefault();
}

function preventPreviewTextKeydown(event: KeyboardEvent) {
  const allowedShortcut = (event.metaKey || event.ctrlKey) && ["a", "c"].includes(event.key.toLowerCase());
  const allowedNavigation = [
    "ArrowLeft",
    "ArrowRight",
    "ArrowUp",
    "ArrowDown",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "Escape",
    "Tab",
  ].includes(event.key);
  if (allowedShortcut || allowedNavigation) {
    return;
  }

  event.preventDefault();
}

function queueSelectionUpdate() {
  requestAnimationFrame(updateSelectionState);
}

function updateSelectionState() {
  const selection = document.getSelection();
  const editor = selectedAbilityEditor(selection);
  const range = editor && selection?.rangeCount ? selection.getRangeAt(0) : null;
  const snapshot = editor && range ? selectionSnapshotFromRange(range, editor) : null;

  toolbarVisible.value = Boolean(editor && snapshot);
  activeEditor.value = editor;
  savedSelectionSnapshot.value = snapshot;
  toolbarFormatState.value = editor && range && snapshot
    ? readSelectionFormatState(range, editor)
    : { ...emptyFormatState };
}

function selectedAbilityEditor(selection: Selection | null) {
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
    return null;
  }

  const range = selection.getRangeAt(0);
  const editor = closestAbilityEditor(range.commonAncestorContainer);
  if (!editor || !previewRoot.value?.contains(editor)) {
    return null;
  }
  return editor;
}

function closestAbilityEditor(node: Node) {
  const element = node.nodeType === 1 ? node as Element : node.parentElement;
  return element?.closest(".role-ability-editor") as HTMLElement | null;
}

function applyInlineCommand(command: "bold" | "italic" | "underline") {
  applyEditorCommand(command, undefined, toolbarFormatState.value[command] ? "remove" : "apply");
}

function applyTextColor(option: TextColorOption) {
  const shouldClear = option.clear || colorsMatch(toolbarFormatState.value.textColor, option.color);
  applyEditorCommand("foreColor", shouldClear ? undefined : option.color, shouldClear ? "remove" : "apply");
}

function applyBackgroundColor(option: TextColorOption) {
  const shouldClear = option.clear || colorsMatch(toolbarFormatState.value.backgroundColor, option.color);
  applyEditorCommand("hiliteColor", shouldClear ? undefined : option.color, shouldClear ? "remove" : "apply");
}

function applyEditorCommand(command: string, value?: string, mode: "apply" | "remove" = "apply") {
  const snapshot = savedSelectionSnapshot.value;
  const editor = editorForSelectionSnapshot(snapshot);
  if (!editor || !snapshot || snapshot.start === snapshot.end) {
    return;
  }

  normalizeAbilityEditorStyles(editor);
  const commandRange = rangeFromTextOffsets(editor, snapshot.start, snapshot.end);
  if (!commandRange) {
    return;
  }

  restoreSelection();
  const textNodes = isolateTextNodesInOffsetRange(editor, snapshot.start, snapshot.end);
  if (!textNodes.length) {
    return;
  }

  textNodes.forEach((node) => applyFormatToTextNode(node, command, value, mode, editor));
  mergeAdjacentStyleWrappers(editor);
  const nextRange = rangeFromTextOffsets(editor, snapshot.start, snapshot.end) ?? commandRange;
  const selection = document.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(nextRange);
  const nextFormatState = commandFormatState(readSelectionFormatState(nextRange, editor), command, value, mode);
  const role = findRoleById(editor.dataset.roleId);
  if (role) {
    saveAbilityEditor(role, editor);
  }
  syncToolbarState(editor, nextRange, nextFormatState, snapshot);
  void nextTick(() => restoreSelectionSnapshot(snapshot, nextFormatState));
  requestAnimationFrame(() => restoreSelectionSnapshot(snapshot, nextFormatState));
}

function applyFormatToTextNode(
  node: Text,
  command: string,
  value: string | undefined,
  mode: "apply" | "remove",
  editor: HTMLElement,
) {
  const wrapper = isolatedStyleWrapperForTextNode(node, editor);
  if (mode === "apply") {
    applyStyleCommand(wrapper, command, value);
  } else {
    removeStyleCommand(wrapper, command);
  }
  cleanupStyleWrapper(wrapper);
  return wrapper;
}

function isolatedStyleWrapperForTextNode(node: Text, editor: HTMLElement) {
  const parent = parentElement(node);
  if (parent !== editor && parent.dataset.abilityStyle === "true") {
    return isolateNodeInStyleWrapper(parent, node);
  }

  const wrapper = document.createElement("span");
  wrapper.dataset.abilityStyle = "true";
  parent.insertBefore(wrapper, node);
  wrapper.appendChild(node);
  return wrapper;
}

function isolateNodeInStyleWrapper(wrapper: HTMLElement, node: Text) {
  if (wrapper.childNodes.length === 1) {
    return wrapper;
  }

  const parent = wrapper.parentNode;
  const children = Array.from(wrapper.childNodes);
  const nodeIndex = children.indexOf(node);
  if (!parent || nodeIndex < 0) {
    return wrapper;
  }

  const beforeWrapper = cloneStyleWrapper(wrapper);
  const selectedWrapper = cloneStyleWrapper(wrapper);
  const afterWrapper = cloneStyleWrapper(wrapper);

  children.slice(0, nodeIndex).forEach((child) => beforeWrapper.appendChild(child));
  selectedWrapper.appendChild(node);
  children.slice(nodeIndex + 1).forEach((child) => afterWrapper.appendChild(child));

  if (beforeWrapper.childNodes.length) {
    parent.insertBefore(beforeWrapper, wrapper);
  }
  parent.insertBefore(selectedWrapper, wrapper);
  if (afterWrapper.childNodes.length) {
    parent.insertBefore(afterWrapper, wrapper);
  }
  parent.removeChild(wrapper);
  return selectedWrapper;
}

function cloneStyleWrapper(wrapper: HTMLElement) {
  const clone = wrapper.cloneNode(false) as HTMLElement;
  clone.dataset.abilityStyle = "true";
  return clone;
}

function applyStyleCommand(wrapper: HTMLElement, command: string, value?: string) {
  if (command === "bold") {
    wrapper.style.fontWeight = "900";
  } else if (command === "italic") {
    wrapper.style.fontStyle = "italic";
  } else if (command === "underline") {
    wrapper.style.textDecoration = "underline";
  } else if (command === "foreColor" && value) {
    wrapper.style.color = value;
    wrapper.style.fontWeight = "900";
  } else if (command === "hiliteColor" && value) {
    wrapper.style.backgroundColor = value;
    if (value !== "transparent") {
      wrapper.style.fontWeight = "900";
    }
  }
}

function removeStyleCommand(wrapper: HTMLElement, command: string) {
  if (command === "bold") {
    wrapper.style.fontWeight = "650";
  } else if (command === "italic") {
    wrapper.style.fontStyle = "normal";
  } else if (command === "underline") {
    wrapper.style.textDecoration = "none";
  } else if (command === "foreColor") {
    wrapper.style.color = DEFAULT_TEXT_COLOR;
    wrapper.style.fontWeight = "650";
  } else if (command === "hiliteColor") {
    wrapper.style.backgroundColor = SCRIPT_PAGE_BACKGROUND;
    wrapper.style.fontWeight = "650";
  }
}

function cleanupStyleWrapper(wrapper: HTMLElement) {
  if (wrapper.getAttribute("style") === "") {
    wrapper.removeAttribute("style");
  }
}

function normalizeAbilityEditorStyles(editor: HTMLElement) {
  const normalizedNodes: Node[] = [];

  function collect(node: Node) {
    if (node instanceof Text) {
      const text = node.textContent ?? "";
      if (text) {
        normalizedNodes.push(styleWrapperFromTextNode(node, editor, text));
      }
      return;
    }

    if (node instanceof HTMLBRElement) {
      normalizedNodes.push(document.createElement("br"));
      return;
    }

    Array.from(node.childNodes).forEach(collect);
  }

  Array.from(editor.childNodes).forEach(collect);
  editor.replaceChildren(...normalizedNodes);
  mergeAdjacentStyleWrappers(editor);
}

function styleWrapperFromTextNode(node: Text, editor: HTMLElement, text: string) {
  const wrapper = document.createElement("span");
  wrapper.dataset.abilityStyle = "true";
  wrapper.textContent = text;
  applyStyleSnapshot(wrapper, {
    bold: textNodeHasBold(node, editor),
    italic: textNodeHasItalic(node, editor),
    underline: textNodeHasVisibleUnderline(node, editor),
    color: textNodeTextColor(node) ?? undefined,
    backgroundColor: textNodeBackgroundColor(node, editor) ?? undefined,
  });
  cleanupStyleWrapper(wrapper);
  return wrapper;
}

function applyStyleSnapshot(wrapper: HTMLElement, style: ExportTextStyle) {
  if (style.bold) {
    wrapper.style.fontWeight = "900";
  }
  if (style.italic) {
    wrapper.style.fontStyle = "italic";
  }
  if (style.underline) {
    wrapper.style.textDecoration = "underline";
  }
  if (style.color) {
    wrapper.style.color = style.color;
  }
  if (style.backgroundColor) {
    wrapper.style.backgroundColor = style.backgroundColor;
  }
}

function mergeAdjacentStyleWrappers(editor: HTMLElement) {
  let previous: HTMLElement | null = null;

  for (const node of Array.from(editor.childNodes)) {
    if (!isAbilityStyleWrapper(node)) {
      previous = null;
      continue;
    }

    if (previous && styleWrapperKey(previous) === styleWrapperKey(node)) {
      while (node.firstChild) {
        previous.appendChild(node.firstChild);
      }
      node.remove();
      continue;
    }

    previous = node;
  }
}

function isAbilityStyleWrapper(node: Node): node is HTMLElement {
  return node instanceof HTMLElement && node.dataset.abilityStyle === "true";
}

function styleWrapperKey(wrapper: HTMLElement) {
  return wrapper.getAttribute("style") ?? "";
}

function syncToolbarState(
  editor: HTMLElement,
  range: Range,
  formatState: FormatState,
  snapshot = selectionSnapshotFromRange(range, editor),
) {
  activeEditor.value = editor;
  savedSelectionSnapshot.value = snapshot;
  toolbarVisible.value = true;
  toolbarFormatState.value = formatState;
}

function commandFormatState(formatState: FormatState, command: string, value: string | undefined, mode: "apply" | "remove") {
  const nextState = { ...formatState };
  if (command === "bold") {
    nextState.bold = mode === "apply";
  }
  if (command === "italic") {
    nextState.italic = mode === "apply";
  }
  if (command === "underline") {
    nextState.underline = mode === "apply";
  }
  if (command === "foreColor") {
    nextState.textColor = mode === "apply" && value ? value : null;
    if (mode === "remove") {
      nextState.bold = false;
    }
  }
  if (command === "hiliteColor") {
    nextState.backgroundColor = mode === "apply" && value ? value : null;
    if (mode === "remove") {
      nextState.bold = false;
    }
  }
  return nextState;
}

function removeFormatFromNode(node: Node, command: string) {
  Array.from(node.childNodes).forEach((child) => removeFormatFromNode(child, command));
  if (!(node instanceof HTMLElement)) {
    return;
  }

  const tagName = node.tagName.toLowerCase();
  if (command === "bold") {
    if (tagName === "strong" || tagName === "b") {
      unwrapElement(node);
      return;
    }
    node.style.fontWeight = "";
  }

  if (command === "italic") {
    if (tagName === "em" || tagName === "i") {
      unwrapElement(node);
      return;
    }
    node.style.fontStyle = "";
  }

  if (command === "underline") {
    if (tagName === "u") {
      unwrapElement(node);
      return;
    }
    node.style.textDecoration = "";
    node.style.textDecorationLine = "";
  }

  if (command === "foreColor") {
    node.style.color = "";
    clearAutomaticWeight(node);
  }

  if (command === "hiliteColor") {
    node.style.backgroundColor = "";
    clearAutomaticWeight(node);
  }

  cleanupElement(node);
}

function clearAutomaticWeight(element: HTMLElement) {
  if (element.style.color || element.style.backgroundColor) {
    return;
  }
  if (element.style.fontWeight === "900") {
    element.style.fontWeight = "";
  }
}

function cleanupElement(element: HTMLElement) {
  if (element.getAttribute("style") === "") {
    element.removeAttribute("style");
  }
  if (element.tagName.toLowerCase() === "span" && element.attributes.length === 0) {
    unwrapElement(element);
  }
}

function unwrapElement(element: HTMLElement) {
  const parent = element.parentNode;
  if (!parent) {
    return;
  }
  while (element.firstChild) {
    parent.insertBefore(element.firstChild, element);
  }
  parent.removeChild(element);
}

function clearSharedFormatAncestor(editor: HTMLElement, range: Range, command: string) {
  const nodes = selectedTextNodes(range, editor);
  if (!nodes.length) {
    return null;
  }

  const firstAncestor = formatAncestorForNode(nodes[0], command, editor);
  if (!firstAncestor) {
    return null;
  }
  if (!nodes.every((node) => formatAncestorForNode(node, command, editor) === firstAncestor)) {
    return null;
  }

  const ancestorRange = document.createRange();
  ancestorRange.selectNodeContents(firstAncestor);
  if (!rangeCoversRange(range, ancestorRange)) {
    return null;
  }

  clearFormatOnElement(firstAncestor, command);
  const nextRange = document.createRange();
  nextRange.selectNodeContents(firstAncestor);
  return nextRange;
}

function formatAncestorForNode(node: Text, command: string, editor: HTMLElement) {
  return ancestorElements(node, editor).find((element) => elementHasFormatForCommand(element, command)) ?? null;
}

function ancestorElements(node: Node, editor: HTMLElement) {
  const elements: HTMLElement[] = [];
  let element: HTMLElement | null = parentElement(node);
  while (element && element !== editor) {
    elements.push(element);
    element = element.parentElement as HTMLElement | null;
  }
  return elements;
}

function elementHasFormatForCommand(element: HTMLElement, command: string) {
  if (command === "bold") {
    return elementAppliesBold(element);
  }
  if (command === "italic") {
    return elementAppliesItalic(element);
  }
  if (command === "underline") {
    return elementAppliesUnderline(element);
  }
  if (command === "foreColor") {
    return Boolean(element.style.color && !colorsMatch(getComputedStyle(element).color, DEFAULT_TEXT_COLOR));
  }
  if (command === "hiliteColor") {
    return isVisibleHighlightColor(element.style.backgroundColor);
  }
  return false;
}

function clearFormatOnElement(element: HTMLElement, command: string) {
  if (command === "bold") {
    element.style.fontWeight = "650";
  }
  if (command === "italic") {
    element.style.fontStyle = "normal";
  }
  if (command === "underline") {
    element.style.textDecoration = "none";
  }
  if (command === "foreColor") {
    element.style.color = DEFAULT_TEXT_COLOR;
    element.style.fontWeight = "650";
  }
  if (command === "hiliteColor") {
    element.style.backgroundColor = SCRIPT_PAGE_BACKGROUND;
    element.style.fontWeight = "650";
  }
}

function rangeCoversRange(range: Range, targetRange: Range) {
  return (
    range.compareBoundaryPoints(Range.START_TO_START, targetRange) <= 0 &&
    range.compareBoundaryPoints(Range.END_TO_END, targetRange) >= 0
  );
}

function readSelectionFormatState(range: Range, editor: HTMLElement): FormatState {
  const nodes = selectedTextNodes(range, editor);
  if (!nodes.length) {
    return { ...emptyFormatState };
  }

  return {
    bold: nodes.every((node) => textNodeHasBold(node, editor)),
    italic: nodes.every((node) => textNodeHasItalic(node, editor)),
    underline: nodes.every((node) => textNodeHasUnderline(node, editor)),
    textColor: commonSelectionValue(nodes, (node) => textNodeTextColor(node)),
    backgroundColor: commonSelectionValue(nodes, (node) => textNodeBackgroundColor(node, editor)),
  };
}

function selectedTextNodes(range: Range, editor: HTMLElement) {
  const snapshot = selectionSnapshotFromRange(range, editor);
  if (!snapshot) {
    return [];
  }
  return textNodesOverlappingOffsets(editor, snapshot.start, snapshot.end).map((segment) => segment.node);
}

function isolateTextNodesInOffsetRange(editor: HTMLElement, start: number, end: number) {
  const segments = textNodesOverlappingOffsets(editor, start, end);
  const nodes: Text[] = [];

  for (const segment of segments) {
    let selectedNode = segment.node;
    if (segment.end < selectedNode.length) {
      selectedNode.splitText(segment.end);
    }
    if (segment.start > 0) {
      selectedNode = selectedNode.splitText(segment.start);
    }
    if (selectedNode.textContent) {
      nodes.push(selectedNode);
    }
  }

  return nodes;
}

function textNodesOverlappingOffsets(editor: HTMLElement, start: number, end: number) {
  const segments: TextSegment[] = [];
  let cursor = 0;
  for (const node of editorTextNodes(editor)) {
    const nodeStart = cursor;
    const nodeEnd = nodeStart + node.length;
    cursor = nodeEnd;
    if (nodeEnd <= start || nodeStart >= end) {
      continue;
    }
    segments.push({
      node,
      start: Math.max(0, start - nodeStart),
      end: Math.min(node.length, end - nodeStart),
    });
  }
  return segments.filter((segment) => segment.start < segment.end);
}

function editorTextNodes(editor: HTMLElement) {
  const nodes: Text[] = [];
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      return node.textContent ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });
  let current = walker.nextNode();
  while (current) {
    nodes.push(current as Text);
    current = walker.nextNode();
  }
  return nodes;
}

function selectionSnapshotFromRange(range: Range, editor: HTMLElement): SelectionSnapshot | null {
  const roleId = editor.dataset.roleId;
  if (!roleId) {
    return null;
  }
  const start = textOffsetAt(editor, range.startContainer, range.startOffset);
  const end = textOffsetAt(editor, range.endContainer, range.endOffset);
  if (start === null || end === null || start === end) {
    return null;
  }
  return {
    roleId,
    start: Math.min(start, end),
    end: Math.max(start, end),
  };
}

function textOffsetAt(editor: HTMLElement, container: Node, offset: number) {
  let textOffset = 0;

  function visit(node: Node): boolean {
    if (node === container) {
      if (node instanceof Text) {
        textOffset += clampOffset(offset, node.length);
      } else {
        const children = Array.from(node.childNodes).slice(0, offset);
        textOffset += children.reduce((total, child) => total + nodeTextLength(child), 0);
      }
      return true;
    }

    if (node instanceof Text) {
      textOffset += node.length;
      return false;
    }

    for (const child of Array.from(node.childNodes)) {
      if (visit(child)) {
        return true;
      }
    }
    return false;
  }

  return visit(editor) ? textOffset : null;
}

function nodeTextLength(node: Node): number {
  if (node instanceof Text) {
    return node.length;
  }
  return Array.from(node.childNodes).reduce((total, child) => total + nodeTextLength(child), 0);
}

function rangeFromTextOffsets(editor: HTMLElement, start: number, end: number) {
  const range = document.createRange();
  const nodes = editorTextNodes(editor);
  if (!nodes.length) {
    return null;
  }

  let cursor = 0;
  let started = false;
  for (const node of nodes) {
    const nodeStart = cursor;
    const nodeEnd = nodeStart + node.length;

    if (!started && (start < nodeEnd || (start === 0 && nodeStart === 0))) {
      range.setStart(node, clampOffset(start - nodeStart, node.length));
      started = true;
    }
    if (started && end <= nodeEnd) {
      range.setEnd(node, clampOffset(end - nodeStart, node.length));
      return range;
    }
    cursor = nodeEnd;
  }

  const lastNode = nodes[nodes.length - 1];
  if (!started) {
    range.setStart(lastNode, lastNode.length);
  }
  range.setEnd(lastNode, lastNode.length);
  return range;
}

function clampOffset(value: number, length: number) {
  return Math.max(0, Math.min(length, value));
}

function textNodeHasBold(node: Text, editor: HTMLElement) {
  for (const element of ancestorElements(node, editor)) {
    if (elementClearsBold(element)) {
      return false;
    }
    if (elementAppliesBold(element)) {
      return true;
    }
  }

  const weight = getComputedStyle(parentElement(node)).fontWeight;
  if (weight === "bold") {
    return true;
  }
  return Number.parseInt(weight, 10) >= 800;
}

function textNodeHasItalic(node: Text, editor: HTMLElement) {
  for (const element of ancestorElements(node, editor)) {
    if (elementClearsItalic(element)) {
      return false;
    }
    if (elementAppliesItalic(element)) {
      return true;
    }
  }

  return getComputedStyle(parentElement(node)).fontStyle !== "normal";
}

function textNodeHasUnderline(node: Text, editor: HTMLElement) {
  for (const element of ancestorElements(node, editor)) {
    if (elementClearsUnderline(element)) {
      return false;
    }
    if (elementAppliesUnderline(element)) {
      return true;
    }
  }

  return getComputedStyle(parentElement(node)).textDecorationLine.includes("underline");
}

function textNodeHasVisibleUnderline(node: Text, editor: HTMLElement) {
  return (
    ancestorElements(node, editor).some((element) => elementAppliesUnderline(element)) ||
    getComputedStyle(parentElement(node)).textDecorationLine.includes("underline")
  );
}

function elementClearsBold(element: HTMLElement) {
  const inlineWeight = element.style.fontWeight;
  if (!inlineWeight || inlineWeight === "bold") {
    return false;
  }
  if (inlineWeight === "normal") {
    return true;
  }
  const numericWeight = Number.parseInt(inlineWeight, 10);
  return !Number.isNaN(numericWeight) && numericWeight < 800;
}

function elementAppliesBold(element: HTMLElement) {
  const inlineWeight = element.style.fontWeight;
  if (inlineWeight) {
    return inlineWeight === "bold" || Number.parseInt(inlineWeight, 10) >= 800;
  }
  return element.tagName === "STRONG" || element.tagName === "B";
}

function elementClearsItalic(element: HTMLElement) {
  return element.style.fontStyle === "normal";
}

function elementAppliesItalic(element: HTMLElement) {
  if (element.style.fontStyle) {
    return element.style.fontStyle !== "normal";
  }
  return element.tagName === "EM" || element.tagName === "I";
}

function elementClearsUnderline(element: HTMLElement) {
  return element.style.textDecoration === "none" || element.style.textDecorationLine === "none";
}

function elementAppliesUnderline(element: HTMLElement) {
  return (
    element.tagName === "U" ||
    element.style.textDecoration.includes("underline") ||
    element.style.textDecorationLine.includes("underline")
  );
}

function textNodeTextColor(node: Text) {
  const color = getComputedStyle(parentElement(node)).color;
  return colorsMatch(color, DEFAULT_TEXT_COLOR) ? null : color;
}

function textNodeBackgroundColor(node: Text, editor: HTMLElement) {
  let element: HTMLElement | null = parentElement(node);
  while (element && element !== editor) {
    const backgroundColor = getComputedStyle(element).backgroundColor;
    if (colorsMatch(backgroundColor, SCRIPT_PAGE_BACKGROUND)) {
      return null;
    }
    if (isVisibleHighlightColor(backgroundColor)) {
      return backgroundColor;
    }
    element = element.parentElement;
  }
  return null;
}

function isVisibleHighlightColor(color?: string | null) {
  return Boolean(
    color &&
    color !== "transparent" &&
    color !== TRANSPARENT_COLOR &&
    !colorsMatch(color, SCRIPT_PAGE_BACKGROUND),
  );
}

function parentElement(node: Node) {
  return (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement) as HTMLElement;
}

function commonSelectionValue(nodes: Text[], readValue: (node: Text) => string | null) {
  const firstValue = readValue(nodes[0]);
  if (!firstValue) {
    return null;
  }
  return nodes.every((node) => colorsMatch(readValue(node), firstValue)) ? firstValue : null;
}

function isTextColorActive(option: TextColorOption) {
  return option.clear ? !toolbarFormatState.value.textColor : colorsMatch(toolbarFormatState.value.textColor, option.color);
}

function isBackgroundColorActive(option: TextColorOption) {
  return option.clear
    ? !toolbarFormatState.value.backgroundColor
    : colorsMatch(toolbarFormatState.value.backgroundColor, option.color);
}

function colorsMatch(left?: string | null, right?: string | null) {
  if (!left || !right) {
    return false;
  }
  return left.replace(/\s+/g, "").toLowerCase() === right.replace(/\s+/g, "").toLowerCase();
}

function restoreSelection() {
  const snapshot = savedSelectionSnapshot.value;
  restoreSelectionSnapshot(snapshot);
}

function restoreSelectionSnapshot(snapshot: SelectionSnapshot | null, formatState?: FormatState) {
  const editor = editorForSelectionSnapshot(snapshot);
  if (!snapshot || !editor) {
    return;
  }
  const range = rangeFromTextOffsets(editor, snapshot.start, snapshot.end);
  if (!range) {
    return;
  }
  const selection = document.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
  if (formatState) {
    syncToolbarState(editor, range, formatState, snapshot);
  }
}

function editorForSelectionSnapshot(snapshot: SelectionSnapshot | null) {
  if (!snapshot) {
    return null;
  }
  if (activeEditor.value?.dataset.roleId === snapshot.roleId && previewRoot.value?.contains(activeEditor.value)) {
    return activeEditor.value;
  }
  return Array.from(previewRoot.value?.querySelectorAll<HTMLElement>(".role-ability-editor") ?? [])
    .find((editor) => editor.dataset.roleId === snapshot.roleId) ?? null;
}

function findRoleById(roleId?: string) {
  if (!roleId) {
    return null;
  }
  for (const team of Object.values(props.script.teams)) {
    const role = team.roles.find((candidate) => candidate.id === roleId);
    if (role) {
      return role;
    }
  }
  return props.script.fabled.find((candidate) => candidate.id === roleId) ?? null;
}

interface ExportTextStyle {
  color?: string;
  backgroundColor?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
}

interface SelectionSnapshot {
  roleId: string;
  start: number;
  end: number;
}

interface TextSegment {
  node: Text;
  start: number;
  end: number;
}

interface ExportTextToken {
  text: string;
  style: ExportTextStyle;
}

async function exportPreviewImage() {
  const svg = previewRoot.value?.querySelector<SVGSVGElement>("svg.script-svg");
  if (!svg) {
    return;
  }

  const exportSvg = svg.cloneNode(true) as SVGSVGElement;
  const exportHeight = previewLayout.value.pageHeight;
  const exportWidth = PAGE_WIDTH;
  exportSvg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  exportSvg.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  exportSvg.setAttribute("width", String(exportWidth));
  exportSvg.setAttribute("height", String(exportHeight));
  exportSvg.setAttribute("viewBox", `${PAGE_X} ${PAGE_Y} ${exportWidth} ${exportHeight}`);
  addExportStyles(exportSvg);
  await inlineExportImages(exportSvg);
  replaceExportForeignObjects(exportSvg);

  const svgText = new XMLSerializer().serializeToString(exportSvg);
  const fileName = safeExportFileName(props.script.name || "剧本");

  try {
    const pngBlob = await renderSvgToPng(svgText, exportWidth, exportHeight);
    downloadBlob(pngBlob, `${fileName}.png`);
  } catch (error) {
    console.error("导出 PNG 失败。", error);
  }
}

function addExportStyles(svg: SVGSVGElement) {
  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent = `
    .script-svg {
      background: transparent;
      font-family: "Noto Serif SC", "Songti SC", STSong, serif;
      user-select: none;
    }

    .svg-script-title {
      fill: #332018;
      font-family: "Noto Serif SC", "Songti SC", STSong, serif;
      font-weight: 900;
    }

    .svg-script-author,
    .svg-section-heading,
    .svg-role-name {
      font-family: "Noto Serif SC", "Songti SC", STSong, serif;
      font-weight: 900;
    }

    .svg-script-author {
      fill: #26313f;
    }

    .role-ability-editor {
      box-sizing: border-box;
      width: 100%;
      height: 100%;
      overflow: hidden;
      color: #141a22;
      font-family: "Noto Serif SC", "Songti SC", STSong, serif;
      font-weight: 650;
      outline: none;
      user-select: text;
      white-space: normal;
      word-break: break-all;
    }

    .role-ability-editor strong {
      font-weight: 900;
    }

    .role-ability-editor .ability-bracket-highlight {
      padding: 0 2px;
      border-radius: 3px;
      background: #e5e7eb;
      font-style: italic;
      font-weight: 900;
    }

    .svg-role-fallback,
    .svg-night-fallback {
      font-weight: 900;
    }

    .svg-night-bar {
      fill: #201713;
      stroke: rgba(255, 255, 255, 0.16);
      stroke-width: 1px;
    }

    .svg-night-label {
      fill: #ffffff;
      font-weight: 900;
    }
  `;
  svg.insertBefore(style, svg.firstChild);
}

function replaceExportForeignObjects(svg: SVGSVGElement) {
  svg.querySelectorAll<SVGForeignObjectElement>("foreignObject.svg-role-ability-object").forEach((foreignObject) => {
    const editor = foreignObject.querySelector<HTMLElement>(".role-ability-editor");
    if (!editor || !foreignObject.parentNode) {
      foreignObject.remove();
      return;
    }

    foreignObject.parentNode.replaceChild(createExportAbilityGroup(foreignObject, editor), foreignObject);
  });
}

function createExportAbilityGroup(foreignObject: SVGForeignObjectElement, editor: HTMLElement) {
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const x = svgAttributeNumber(foreignObject, "x");
  const y = svgAttributeNumber(foreignObject, "y");
  const width = svgAttributeNumber(foreignObject, "width");
  const lines = wrapExportTokens(readExportTextTokens(editor), width, ROLE_ABILITY_FONT_SIZE);

  lines.forEach((line, lineIndex) => {
    const textY = y + ROLE_ABILITY_FONT_SIZE + lineIndex * ROLE_ABILITY_LINE_HEIGHT;
    let cursorX = x;

    line.forEach((token) => {
      const tokenWidth = estimateTextWidth(token.text, ROLE_ABILITY_FONT_SIZE);
      if (token.style.backgroundColor) {
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", String(cursorX - 1));
        rect.setAttribute("y", String(textY - ROLE_ABILITY_FONT_SIZE + 2));
        rect.setAttribute("width", String(tokenWidth + 2));
        rect.setAttribute("height", String(ROLE_ABILITY_LINE_HEIGHT - 2));
        rect.setAttribute("rx", "3");
        rect.setAttribute("fill", token.style.backgroundColor);
        group.appendChild(rect);
      }
      cursorX += tokenWidth;
    });

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(x));
    text.setAttribute("y", String(textY));
    text.setAttribute("fill", DEFAULT_TEXT_COLOR);
    text.setAttribute("font-family", "\"Noto Serif SC\", \"Songti SC\", STSong, serif");
    text.setAttribute("font-size", String(ROLE_ABILITY_FONT_SIZE));
    text.setAttribute("font-weight", "650");

    line.forEach((token) => {
      const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      tspan.textContent = token.text;
      if (token.style.color) {
        tspan.setAttribute("fill", token.style.color);
      }
      if (token.style.bold) {
        tspan.setAttribute("font-weight", "900");
      }
      if (token.style.italic) {
        tspan.setAttribute("font-style", "italic");
      }
      if (token.style.underline) {
        tspan.setAttribute("text-decoration", "underline");
      }
      text.appendChild(tspan);
    });

    group.appendChild(text);
  });

  return group;
}

function svgAttributeNumber(element: Element, attribute: string) {
  const value = Number(element.getAttribute(attribute));
  return Number.isFinite(value) ? value : 0;
}

function readExportTextTokens(editor: HTMLElement) {
  const tokens: ExportTextToken[] = [];
  editor.childNodes.forEach((node) => collectExportTextTokens(node, {}, tokens));
  return tokens.length ? tokens : [{ text: "", style: {} }];
}

function collectExportTextTokens(node: Node, inheritedStyle: ExportTextStyle, tokens: ExportTextToken[]) {
  if (node.nodeType === Node.TEXT_NODE) {
    appendExportTextToken(tokens, node.textContent ?? "", inheritedStyle);
    return;
  }
  if (!(node instanceof HTMLElement)) {
    return;
  }

  if (node.tagName.toLowerCase() === "br") {
    appendExportTextToken(tokens, "\n", inheritedStyle);
    return;
  }

  const nextStyle = exportStyleForElement(node, inheritedStyle);
  node.childNodes.forEach((child) => collectExportTextTokens(child, nextStyle, tokens));
}

function exportStyleForElement(element: HTMLElement, inheritedStyle: ExportTextStyle) {
  const style: ExportTextStyle = { ...inheritedStyle };
  const tagName = element.tagName.toLowerCase();

  if (tagName === "strong" || tagName === "b") {
    style.bold = true;
  }
  if (tagName === "em" || tagName === "i") {
    style.italic = true;
  }
  if (tagName === "u") {
    style.underline = true;
  }
  if (element.classList.contains("ability-bracket-highlight")) {
    style.backgroundColor = "#e5e7eb";
    style.bold = true;
    style.italic = true;
  }

  if (element.style.color) {
    style.color = colorsMatch(element.style.color, DEFAULT_TEXT_COLOR) ? undefined : element.style.color;
  }
  if (element.style.backgroundColor) {
    style.backgroundColor = isVisibleExportBackground(element.style.backgroundColor)
      ? element.style.backgroundColor
      : undefined;
  }
  if (element.style.fontWeight) {
    const weight = Number.parseInt(element.style.fontWeight, 10);
    style.bold = element.style.fontWeight === "bold" || (!Number.isNaN(weight) && weight >= 800);
  }
  if (element.style.fontStyle) {
    style.italic = element.style.fontStyle !== "normal";
  }
  if (element.style.textDecoration || element.style.textDecorationLine) {
    const decoration = `${element.style.textDecoration} ${element.style.textDecorationLine}`;
    if (decoration.includes("underline")) {
      style.underline = true;
    } else if (decoration.includes("none")) {
      style.underline = false;
    }
  }

  return style;
}

function isVisibleExportBackground(color: string) {
  return color !== "transparent" && !colorsMatch(color, TRANSPARENT_COLOR) && !colorsMatch(color, SCRIPT_PAGE_BACKGROUND);
}

function wrapExportTokens(tokens: ExportTextToken[], maxWidth: number, fontSize: number) {
  const maxUnits = Math.max(4, maxWidth / fontSize);
  const lines: ExportTextToken[][] = [[]];
  let lineWidth = 0;

  for (const token of tokens) {
    for (const char of Array.from(token.text)) {
      if (char === "\n") {
        lines.push([]);
        lineWidth = 0;
        continue;
      }

      const charWidth = charWidthUnits(char);
      if (lines[lines.length - 1].length > 0 && lineWidth + charWidth > maxUnits) {
        lines.push([]);
        lineWidth = 0;
      }
      if (lines[lines.length - 1].length === 0 && !char.trim()) {
        continue;
      }

      appendExportTextToken(lines[lines.length - 1], char, token.style);
      lineWidth += charWidth;
    }
  }

  return lines.filter((line) => line.length > 0);
}

function appendExportTextToken(tokens: ExportTextToken[], text: string, style: ExportTextStyle) {
  if (!text) {
    return;
  }

  const previous = tokens[tokens.length - 1];
  if (previous && exportTextStylesMatch(previous.style, style)) {
    previous.text += text;
    return;
  }
  tokens.push({ text, style: { ...style } });
}

function exportTextStylesMatch(left: ExportTextStyle, right: ExportTextStyle) {
  return (
    left.bold === right.bold &&
    left.italic === right.italic &&
    left.underline === right.underline &&
    optionalColorsMatch(left.color, right.color) &&
    optionalColorsMatch(left.backgroundColor, right.backgroundColor)
  );
}

function optionalColorsMatch(left?: string, right?: string) {
  if (!left && !right) {
    return true;
  }
  return colorsMatch(left, right);
}

async function inlineExportImages(svg: SVGSVGElement) {
  const images = Array.from(svg.querySelectorAll<SVGImageElement>("image"));
  await Promise.all(
    images.map(async (image) => {
      const href = image.getAttribute("href") || image.getAttribute("xlink:href") || image.href.baseVal;
      if (!href || href.startsWith("data:")) {
        return;
      }

      const dataUrl = await fetchExportImageDataUrl(href);
      if (dataUrl) {
        image.setAttribute("href", dataUrl);
        image.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", dataUrl);
        return;
      }

      clearExportImage(image);
    }),
  );
}

async function fetchExportImageDataUrl(url: string) {
  return (
    await fetchImageDataUrl(url) ??
    await fetchImageDataUrl(`/__image_proxy?url=${encodeURIComponent(url)}`) ??
    await fetchImageDataUrlWithTauri(url)
  );
}

async function fetchImageDataUrl(url: string) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return null;
    }

    const blob = await response.blob();
    const contentType = response.headers.get("content-type") ?? blob.type;
    if (!contentType.startsWith("image/")) {
      return null;
    }
    return await blobToDataUrl(blob);
  } catch {
    return null;
  }
}

async function fetchImageDataUrlWithTauri(url: string) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<string>("fetch_image_data_url", { url });
  } catch {
    return null;
  }
}

function clearExportImage(image: SVGImageElement) {
  image.removeAttribute("href");
  image.removeAttribute("xlink:href");
  image.href.baseVal = "";
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function renderSvgToPng(svgText: string, width: number, height: number) {
  const svgBlob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
  const objectUrl = URL.createObjectURL(svgBlob);

  try {
    const image = await loadImage(objectUrl);
    const pixelRatio = 2;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas is not available.");
    }
    context.scale(pixelRatio, pixelRatio);
    context.clearRect(0, 0, width, height);
    context.drawImage(image, 0, 0, width, height);

    return await new Promise<Blob>((resolve, reject) => {
      try {
        canvas.toBlob((blob) => {
          if (blob) {
            resolve(blob);
            return;
          }
          reject(new Error("Canvas export returned an empty image."));
        }, "image/png");
      } catch (error) {
        reject(error);
      }
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to load exported SVG."));
    image.src = src;
  });
}

function downloadBlob(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

function safeExportFileName(fileName: string) {
  const sanitized = fileName.trim().replace(/[\\/:*?"<>|]+/g, "_");
  return sanitized || "剧本";
}
</script>

<template>
  <section ref="previewRoot" class="preview-pane" aria-label="剧本预览">
    <header class="pane-toolbar">
      <div class="toolbar-title">
        <Eye :size="18" aria-hidden="true" />
        <span>预览</span>
      </div>
      <div class="preview-actions" aria-label="预览操作">
        <label class="preview-action">
          <Upload :size="15" aria-hidden="true" />
          <span>导入 JSON</span>
          <input accept=".json,application/json" type="file" @change="$emit('json-upload', $event)" />
        </label>
        <button class="preview-action" type="button" @click="exportPreviewImage">
          <ImageDown :size="15" aria-hidden="true" />
          <span>导出图片</span>
        </button>
        <button class="preview-action" disabled type="button">
          <FileJson :size="15" aria-hidden="true" />
          <span>导出 JSON</span>
        </button>
      </div>
    </header>

    <div
      ref="previewStage"
      :class="['svg-stage', 'canvas-stage', { panning: isPreviewPanning }]"
      @wheel.prevent="handlePreviewWheel"
      @pointerdown="handlePreviewPointerDown"
      @pointermove="handlePreviewPointerMove"
      @pointerup="handlePreviewPointerUp"
      @pointercancel="handlePreviewPointerUp"
      @auxclick.prevent
    >
      <div class="svg-canvas-content" :style="previewCanvasStyle">
        <svg
          class="script-svg"
          :viewBox="`0 0 ${SVG_WIDTH} ${previewLayout.height}`"
          role="img"
          aria-label="剧本预览"
        >
        <defs>
          <pattern id="preview-dot-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.35" fill="#cbd5e1" />
          </pattern>
          <clipPath id="script-page-clip">
            <rect
              :x="PAGE_X"
              :y="PAGE_Y"
              :width="PAGE_WIDTH"
              :height="previewLayout.pageHeight"
              rx="18"
            />
          </clipPath>
        </defs>

        <!-- <rect width="1100" :height="previewLayout.height" fill="#ffffff" />
        <rect width="1100" :height="previewLayout.height" fill="url(#preview-dot-grid)" opacity="0.6" /> -->
        <rect
          :x="PAGE_X"
          :y="PAGE_Y"
          :width="PAGE_WIDTH"
          :height="previewLayout.pageHeight"
          rx="20"
          fill="#fffdf8"
          stroke="#fffdf8"
          stroke-width="3"
        />

        <g clip-path="url(#script-page-clip)">
          <rect
            class="svg-night-bar"
            :x="LEFT_RAIL_X"
            :y="PAGE_Y"
            :width="RAIL_WIDTH"
            :height="previewLayout.pageHeight"
          />
          <rect
            class="svg-night-bar"
            :x="RIGHT_RAIL_X"
            :y="PAGE_Y"
            :width="RAIL_WIDTH"
            :height="previewLayout.pageHeight"
          />
        </g>

        <g class="svg-night-rail" :transform="`translate(${LEFT_RAIL_X} ${previewLayout.nightRailContentY})`">
          <text
            class="svg-night-label"
            :x="NIGHT_LABEL_X"
            :y="NIGHT_LABEL_FIRST_Y"
            :font-size="NIGHT_LABEL_FONT_SIZE"
            text-anchor="middle"
          >
            首
          </text>
          <text
            class="svg-night-label"
            :x="NIGHT_LABEL_X"
            :y="NIGHT_LABEL_SECOND_Y"
            :font-size="NIGHT_LABEL_FONT_SIZE"
            text-anchor="middle"
          >
            夜
          </text>
          <g
            v-for="(item, index) in previewLayout.firstNightItems"
            :key="item.id"
            :transform="`translate(${NIGHT_ICON_X} ${NIGHT_ICON_START_Y + index * NIGHT_ICON_STEP})`"
          >
            <title>{{ `${item.name} ${formatNightOrder(item.order)}${item.reminder ? `\n${item.reminder}` : ""}` }}</title>
            <image
              v-if="item.image"
              :href="item.image"
              :width="NIGHT_ICON_SIZE"
              :height="NIGHT_ICON_SIZE"
              preserveAspectRatio="xMidYMid meet"
            />
            <template v-else>
              <circle
                :cx="NIGHT_ICON_CENTER"
                :cy="NIGHT_ICON_CENTER"
                :r="NIGHT_ICON_FALLBACK_RADIUS"
                fill="#f8fafc"
                :stroke="item.color"
                stroke-width="2"
              />
              <text
                class="svg-night-fallback"
                :x="NIGHT_ICON_CENTER"
                :y="NIGHT_ICON_CENTER"
                :font-size="NIGHT_FALLBACK_FONT_SIZE"
                text-anchor="middle"
                dominant-baseline="central"
                :fill="item.color"
              >
                {{ item.name.slice(0, 1) }}
              </text>
            </template>
          </g>
        </g>

        <g class="svg-night-rail" :transform="`translate(${RIGHT_RAIL_X} ${previewLayout.nightRailContentY})`">
          <text
            class="svg-night-label"
            :x="NIGHT_LABEL_X"
            :y="NIGHT_LABEL_FIRST_Y"
            :font-size="NIGHT_LABEL_FONT_SIZE"
            text-anchor="middle"
          >
            其
          </text>
          <text
            class="svg-night-label"
            :x="NIGHT_LABEL_X"
            :y="NIGHT_LABEL_SECOND_Y"
            :font-size="NIGHT_LABEL_FONT_SIZE"
            text-anchor="middle"
          >
            他
          </text>
          <g
            v-for="(item, index) in previewLayout.otherNightItems"
            :key="item.id"
            :transform="`translate(${NIGHT_ICON_X} ${NIGHT_ICON_START_Y + index * NIGHT_ICON_STEP})`"
          >
            <title>{{ `${item.name} ${formatNightOrder(item.order)}${item.reminder ? `\n${item.reminder}` : ""}` }}</title>
            <image
              v-if="item.image"
              :href="item.image"
              :width="NIGHT_ICON_SIZE"
              :height="NIGHT_ICON_SIZE"
              preserveAspectRatio="xMidYMid meet"
            />
            <template v-else>
              <circle
                :cx="NIGHT_ICON_CENTER"
                :cy="NIGHT_ICON_CENTER"
                :r="NIGHT_ICON_FALLBACK_RADIUS"
                fill="#f8fafc"
                :stroke="item.color"
                stroke-width="2"
              />
              <text
                class="svg-night-fallback"
                :x="NIGHT_ICON_CENTER"
                :y="NIGHT_ICON_CENTER"
                :font-size="NIGHT_FALLBACK_FONT_SIZE"
                text-anchor="middle"
                dominant-baseline="central"
                :fill="item.color"
              >
                {{ item.name.slice(0, 1) }}
              </text>
            </template>
          </g>
        </g>

        <g class="svg-script-content">
          <text
            class="svg-script-title"
            :x="CONTENT_CENTER"
            :y="HEADER_TITLE_Y"
            :font-size="SCRIPT_TITLE_FONT_SIZE"
            text-anchor="middle"
          >
            {{ script.name }}
          </text>
          <text
            v-if="hasScriptAuthor"
            class="svg-script-author"
            :x="CONTENT_CENTER"
            :y="HEADER_AUTHOR_Y"
            :font-size="SCRIPT_AUTHOR_FONT_SIZE"
            text-anchor="middle"
          >
            剧本作者：{{ script.author }}
          </text>

          <g v-for="section in previewLayout.sections" :key="section.key">
            <text
              class="svg-section-heading"
              :x="CONTENT_X"
              :y="section.headingY"
              :font-size="SECTION_HEADING_FONT_SIZE"
              :fill="section.color"
            >
              {{ section.heading }}
            </text>
            <line
              :x1="section.lineX"
              :x2="CONTENT_RIGHT"
              :y1="section.lineY"
              :y2="section.lineY"
              :stroke="section.color"
              stroke-width="3"
              stroke-linecap="round"
            />

            <g v-for="role in section.roles" :key="role.id">
              <image
                v-if="role.role.image"
                :href="role.role.image"
                :x="role.imageX"
                :y="role.imageY"
                :width="ROLE_ICON_SIZE"
                :height="ROLE_ICON_SIZE"
                preserveAspectRatio="xMidYMid meet"
              />
              <template v-else>
                <circle
                  :cx="role.imageCenterX"
                  :cy="role.imageCenterY"
                  r="26"
                  fill="#fffdf8"
                  :stroke="role.color"
                  stroke-width="2"
                />
                <text
                  class="svg-role-fallback"
                  :x="role.imageCenterX"
                  :y="role.imageCenterY"
                  :font-size="ROLE_FALLBACK_FONT_SIZE"
                  text-anchor="middle"
                  dominant-baseline="central"
                  :fill="role.color"
                >
                  {{ role.fallbackLetter }}
                </text>
              </template>

              <text
                v-for="(line, index) in role.nameLines"
                :key="`name-${index}`"
                class="svg-role-name"
                :x="role.textX"
                :y="role.nameStartY + index * ROLE_NAME_LINE_HEIGHT"
                :font-size="ROLE_NAME_FONT_SIZE"
                :fill="role.color"
              >
                {{ line }}
              </text>
              <foreignObject
                class="svg-role-ability-object"
                :x="role.abilityX"
                :y="role.abilityY"
                :width="role.abilityWidth"
                :height="role.abilityHeight"
              >
                <div
                  xmlns="http://www.w3.org/1999/xhtml"
                  class="role-ability-editor"
                  contenteditable="true"
                  spellcheck="false"
                  :data-role-id="role.id"
                  :style="{
                    fontSize: `${ROLE_ABILITY_FONT_SIZE}px`,
                    lineHeight: `${ROLE_ABILITY_LINE_HEIGHT}px`,
                  }"
                  v-html="roleAbilityHtml(role.role, role.team)"
                  @beforeinput="preventPreviewTextMutation"
                  @blur="handleAbilityBlur(role.role, $event)"
                  @cut="preventPreviewTextMutation"
                  @drop="preventPreviewTextMutation"
                  @keydown="preventPreviewTextKeydown"
                  @keyup="queueSelectionUpdate"
                  @mouseup="queueSelectionUpdate"
                  @paste="preventPreviewTextMutation"
                />
              </foreignObject>
            </g>
          </g>
        </g>
        </svg>
      </div>
    </div>

    <TextFormatToolbar
      :visible="toolbarVisible"
      :format-state="toolbarFormatState"
      :text-color-options="textColorOptions"
      :background-color-options="backgroundColorOptions"
      :is-text-color-active="isTextColorActive"
      :is-background-color-active="isBackgroundColorActive"
      @inline-command="applyInlineCommand"
      @text-color="applyTextColor"
      @background-color="applyBackgroundColor"
    />
  </section>
</template>

<style scoped>
.preview-pane {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-color: #e5e5e5;
  background: transparent;
}

.pane-toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid #e5e5e5;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
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

.preview-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.preview-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 11px;
  border: 1px solid #d8d8d8;
  border-radius: 999px;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  transition:
    background var(--motion-duration-fast) var(--motion-ease-standard),
    border-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard),
    box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.preview-action:hover:not(:disabled) {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
  box-shadow: var(--motion-lift-shadow);
  transform: translateY(-1px);
}

.preview-action:active:not(:disabled) {
  transform: scale(var(--motion-press-scale));
}

.preview-action:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.preview-action input {
  display: none;
}

.svg-stage {
  position: relative;
  min-height: 0;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
}

.svg-stage.panning {
  cursor: grabbing;
}

.svg-canvas-content {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  transition: filter var(--motion-duration-base) var(--motion-ease-standard);
  will-change: transform;
}

.svg-stage.panning .svg-canvas-content {
  filter: saturate(0.98) contrast(0.98);
}

.svg-stage svg {
  display: block;
  width: 100%;
  height: auto;
  filter: drop-shadow(0 22px 38px rgba(15, 23, 42, 0.13));
}

.script-svg {
  font-family: "Noto Serif SC", "Songti SC", STSong, serif;
  letter-spacing: 0;
  text-rendering: geometricPrecision;
  user-select: none;
  -webkit-user-select: none;
}

.script-svg text {
  pointer-events: none;
  user-select: none;
  -webkit-user-select: none;
}

.svg-script-title {
  fill: #3f2b20;
  font-weight: 900;
}

.svg-script-author {
  fill: #26313f;
  font-weight: 750;
}

.svg-section-heading {
  font-weight: 900;
}

.svg-role-name {
  font-weight: 900;
}

.svg-role-ability {
  fill: #141a22;
  font-weight: 650;
}

.svg-role-ability-object {
  overflow: visible;
}

.role-ability-editor {
  width: 100%;
  min-height: 100%;
  overflow: hidden;
  color: #141a22;
  cursor: text;
  font-family: "Noto Serif SC", "Songti SC", STSong, serif;
  font-weight: 650;
  outline: none;
  user-select: text;
  -webkit-user-select: text;
  white-space: normal;
  word-break: break-all;
  transition: background var(--motion-duration-fast) var(--motion-ease-standard);
}

.role-ability-editor:focus {
  background: rgba(0, 0, 0, 0.04);
}

.role-ability-editor :deep(strong) {
  font-weight: 900;
}

.role-ability-editor :deep(.ability-bracket-highlight) {
  padding: 0 2px;
  border-radius: 3px;
  background: #e5e7eb;
  font-style: italic;
  font-weight: 900;
}

.role-ability-editor :deep(span),
.role-ability-editor :deep(strong),
.role-ability-editor :deep(em),
.role-ability-editor :deep(u) {
  user-select: text;
  -webkit-user-select: text;
}

.svg-role-fallback {
  font-weight: 900;
}

.svg-night-bar {
  fill: #201713;
  stroke: rgba(255, 255, 255, 0.16);
  stroke-width: 1px;
}

.svg-night-label {
  fill: #ffffff;
  font-weight: 900;
}

.svg-night-fallback {
  font-weight: 900;
}
</style>
