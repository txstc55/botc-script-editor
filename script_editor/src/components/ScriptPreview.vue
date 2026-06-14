<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Eye } from "@lucide/vue";
import type { ScriptDraft, TeamKey } from "../types";
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

  return [...roleSections, fabledSection].filter((section) => section.roles.length > 0);
});

const allSelectedRoles = computed(() =>
  Object.values(props.script.teams).filter((team) => team.key !== "traveler").flatMap((team) =>
    team.roles
      .filter((role) => role.selected)
      .map((role) => ({ role, team: team.key })),
  ),
);

const firstNightOrder = computed(() => nightOrder("firstNight"));
const otherNightOrder = computed(() => nightOrder("otherNight"));
const hasScriptAuthor = computed(() => props.script.author.trim().length > 0);
const firstSectionY = computed(() =>
  hasScriptAuthor.value ? FIRST_SECTION_WITH_AUTHOR_Y : FIRST_SECTION_WITHOUT_AUTHOR_Y,
);
const previewLayout = computed<SvgPreviewLayout>(() => buildPreviewLayout());
const currentPlayCharacterHighlightRules = computed(() => buildCurrentPlayCharacterHighlightRules());
const previewRoot = ref<HTMLElement | null>(null);
const toolbarVisible = ref(false);
const activeEditor = ref<HTMLElement | null>(null);
const savedSelectionRange = ref<Range | null>(null);
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

function nightOrder(field: "firstNight" | "otherNight"): NightOrderItem[] {
  return allSelectedRoles.value
    .map(({ role, team }) => ({
      id: `${field}-${role.id}`,
      name: role.name,
      image: role.image,
      order: role[field] ?? 0,
      team,
      color: teamColors[team],
    }))
    .filter((item) => item.order > 0)
    .sort((left, right) => left.order - right.order || left.name.localeCompare(right.name, "zh-Hans-CN"));
}

function buildPreviewLayout(): SvgPreviewLayout {
  const sections = buildSections();
  const contentBottom = sections.length
    ? sections[sections.length - 1].y + sections[sections.length - 1].height
    : firstSectionY.value;
  const firstNightStackHeight = nightRailStackHeight(firstNightOrder.value.length);
  const otherNightStackHeight = nightRailStackHeight(otherNightOrder.value.length);
  const nightHeightForFirstCentered = Math.max(
    firstNightStackHeight + NIGHT_RAIL_VERTICAL_MARGIN * 2,
    otherNightStackHeight * 2 - firstNightStackHeight + NIGHT_RAIL_VERTICAL_MARGIN * 2,
  );
  const height = Math.max(MIN_PREVIEW_HEIGHT, contentBottom + 72, PAGE_Y * 2 + nightHeightForFirstCentered);
  const pageHeight = height - PAGE_Y * 2;

  return {
    height,
    pageHeight,
    nightRailContentY: PAGE_Y + (pageHeight - firstNightStackHeight) / 2,
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
    const heading = section.key === "fabled" ? section.label : `${teamSideLabel(section.key)} · ${section.label}`;
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
  saveAbilityEditor(role, event.currentTarget as HTMLElement);
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

  toolbarVisible.value = Boolean(editor);
  activeEditor.value = editor;
  savedSelectionRange.value = range ? range.cloneRange() : null;
  toolbarFormatState.value = editor && range ? readSelectionFormatState(range, editor) : { ...emptyFormatState };
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
  const editor = activeEditor.value;
  const range = savedSelectionRange.value;
  if (!editor || !range || range.collapsed) {
    return;
  }

  restoreSelection();
  const selectedRange = document.getSelection()?.rangeCount ? document.getSelection()?.getRangeAt(0) : range;
  const commandRange = selectedRange ?? range;
  if (mode === "remove") {
    const clearedRange = clearSharedFormatAncestor(editor, commandRange, command);
    if (clearedRange) {
      const nextFormatState = commandFormatState(readSelectionFormatState(clearedRange, editor), command, value, mode);
      const selection = document.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(clearedRange);
      syncToolbarState(editor, clearedRange, nextFormatState);
      requestAnimationFrame(() => syncToolbarState(editor, clearedRange, nextFormatState));
      return;
    }
  }

  const fragment = commandRange.extractContents();
  if (mode === "remove") {
    removeFormatFromNode(fragment, command);
  }
  if (mode === "apply" && (command === "foreColor" || command === "hiliteColor")) {
    removeFormatFromNode(fragment, command);
  }
  const wrapper = mode === "apply" ? createFormatWrapper(command, value) : createRemovalWrapper(command);
  wrapper.appendChild(fragment);
  commandRange.insertNode(wrapper);

  const nextRange = document.createRange();
  nextRange.selectNode(wrapper);
  const selection = document.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(nextRange);
  const nextFormatState = commandFormatState(readSelectionFormatState(nextRange, editor), command, value, mode);
  syncToolbarState(editor, nextRange, nextFormatState);
  requestAnimationFrame(() => syncToolbarState(editor, nextRange, nextFormatState));
}

function createFormatWrapper(command: string, value?: string) {
  if (command === "bold") {
    return document.createElement("strong");
  }
  if (command === "italic") {
    return document.createElement("em");
  }
  if (command === "underline") {
    return document.createElement("u");
  }

  const wrapper = document.createElement("span");
  if (command === "foreColor" && value) {
    wrapper.style.color = value;
    wrapper.style.fontWeight = "900";
  }
  if (command === "hiliteColor" && value) {
    wrapper.style.backgroundColor = value;
    if (value !== "transparent") {
      wrapper.style.fontWeight = "900";
    }
  }
  return wrapper;
}

function createRemovalWrapper(command: string) {
  const wrapper = document.createElement("span");
  if (command === "bold" || command === "foreColor") {
    wrapper.style.fontWeight = "650";
  }
  if (command === "italic") {
    wrapper.style.fontStyle = "normal";
  }
  if (command === "underline") {
    wrapper.style.textDecoration = "none";
  }
  if (command === "foreColor") {
    wrapper.style.color = DEFAULT_TEXT_COLOR;
  }
  if (command === "hiliteColor") {
    wrapper.style.backgroundColor = SCRIPT_PAGE_BACKGROUND;
    wrapper.style.fontWeight = "650";
  }
  return wrapper;
}

function syncToolbarState(editor: HTMLElement, range: Range, formatState: FormatState) {
  activeEditor.value = editor;
  savedSelectionRange.value = range.cloneRange();
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
  const nodes: Text[] = [];
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.textContent?.trim()) {
        return NodeFilter.FILTER_REJECT;
      }
      return range.intersectsNode(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });
  let current = walker.nextNode();
  while (current) {
    nodes.push(current as Text);
    current = walker.nextNode();
  }
  return nodes;
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
  if (!savedSelectionRange.value) {
    return;
  }
  const selection = document.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(savedSelectionRange.value);
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
  return null;
}
</script>

<template>
  <section ref="previewRoot" class="preview-pane" aria-label="剧本预览">
    <header class="pane-toolbar">
      <div class="toolbar-title">
        <Eye :size="18" aria-hidden="true" />
        <span>预览</span>
      </div>
      <div class="preview-stats">
        <span>{{ selectedRoleCount }} 角色</span>
        <span>{{ script.fabled.length }} 传奇角色</span>
        <span>{{ script.jinxes.length }} 相克规则</span>
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
          rx="18"
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
            <title>{{ item.name }}</title>
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
            <title>{{ item.name }}</title>
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
