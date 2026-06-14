import type { JinxDraft, PlayCleanupReport, RoleDraft, ScriptDraft, TeamKey } from "../types";

type RawRecord = Record<string, unknown>;

const TEAM_ALIASES: Record<string, TeamKey> = {
  townsfolk: "townsfolk",
  outsider: "outsider",
  outsiders: "outsider",
  minion: "minion",
  minions: "minion",
  demon: "demon",
  demons: "demon",
  traveler: "traveler",
  travelers: "traveler",
  traveller: "traveler",
  traveller2: "traveler",
};

export const teamLabels: Record<TeamKey, string> = {
  townsfolk: "镇民",
  outsider: "外来者",
  minion: "爪牙",
  demon: "恶魔",
  traveler: "旅行者",
};

export const previewTeamOrder: TeamKey[] = ["townsfolk", "outsider", "minion", "demon"];

export function createEmptyScript(): ScriptDraft {
  return {
    name: "未命名剧本",
    author: "",
    fabled: [],
    jinxes: [],
    teams: {
      townsfolk: { key: "townsfolk", label: teamLabels.townsfolk, roles: [] },
      outsider: { key: "outsider", label: teamLabels.outsider, roles: [] },
      minion: { key: "minion", label: teamLabels.minion, roles: [] },
      demon: { key: "demon", label: teamLabels.demon, roles: [] },
      traveler: { key: "traveler", label: teamLabels.traveler, roles: [] },
    },
  };
}

export function loadPlayFromJson(input: unknown, fileName = "导入剧本.json") {
  const report: PlayCleanupReport = {
    fileName,
    roleCount: 0,
    fabledCount: 0,
    jinxCount: 0,
    skippedCount: 0,
    normalizedTeamCount: 0,
    normalizedJinxTeamCount: 0,
    normalizedSetupCount: 0,
    backfilledReminderCount: 0,
  };
  const script = createEmptyScript();
  const items = extractItems(input);
  const meta = findMeta(input, items);

  script.name = cleanText(meta?.name) || cleanText((input as RawRecord)?.name) || "未命名剧本";
  script.author = cleanText(meta?.author) || cleanText((input as RawRecord)?.author);

  for (const rawItem of items) {
    if (!isRecord(rawItem)) {
      report.skippedCount += 1;
      continue;
    }
    if (cleanText(rawItem.id) === "_meta") {
      continue;
    }

    const normalized = normalizeItem(rawItem, report);
    const name = cleanText(normalized.name);
    const team = normalizeTeam(normalized.team, report);
    if (!name || !team) {
      report.skippedCount += 1;
      continue;
    }

    if (team === "jinx") {
      script.jinxes.push(toJinx(normalized, name));
      report.jinxCount += 1;
      continue;
    }

    if (team === "fabled") {
      script.fabled.push({
        id: cleanText(normalized.id) || name,
        name,
        ability: cleanText(normalized.ability),
        image: cleanText(normalized.image),
      });
      report.fabledCount += 1;
      collectNestedJinxes(script, normalized, name, report);
      continue;
    }

    script.teams[team].roles.push(toRole(normalized, name));
    report.roleCount += 1;
    collectNestedJinxes(script, normalized, name, report);
  }

  return { script, report };
}

function extractItems(input: unknown): unknown[] {
  if (Array.isArray(input)) {
    return input;
  }
  if (!isRecord(input)) {
    return [];
  }

  for (const key of ["characters", "script", "roles", "items", "data"]) {
    const value = input[key];
    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
}

function findMeta(input: unknown, items: unknown[]): RawRecord | undefined {
  const metaItem = items.find((item) => isRecord(item) && cleanText(item.id) === "_meta");
  if (isRecord(metaItem)) {
    return metaItem;
  }
  return isRecord(input) ? input : undefined;
}

function normalizeItem(item: RawRecord, report: PlayCleanupReport): RawRecord {
  const normalized: RawRecord = { ...item };
  const oldSetup = normalized.setup;
  normalized.setup = normalizeSetup(oldSetup);
  if (oldSetup !== undefined && normalized.setup !== oldSetup) {
    report.normalizedSetupCount += 1;
  }

  const ability = cleanText(normalized.ability);
  const firstNightReminder = cleanText(normalized.firstNightReminder ?? normalized.firstReminder);
  if (hasNightOrder(normalized.firstNight) && ability && !firstNightReminder) {
    normalized.firstNightReminder = ability;
    report.backfilledReminderCount += 1;
  }

  const otherNightReminder = cleanText(normalized.otherNightReminder ?? normalized.ogherNightReminder);
  if (hasNightOrder(normalized.otherNight) && ability && !otherNightReminder) {
    normalized.otherNightReminder = ability;
    report.backfilledReminderCount += 1;
  }

  return normalized;
}

function normalizeTeam(value: unknown, report: PlayCleanupReport): TeamKey | "fabled" | "jinx" | null {
  const original = cleanText(value);
  const team = original.toLowerCase();
  if (!team) {
    return null;
  }
  if (team.includes("jinx")) {
    if (team !== "jinx") {
      report.normalizedJinxTeamCount += 1;
    }
    return "jinx";
  }
  if (team === "fabled") {
    return "fabled";
  }
  const normalized = TEAM_ALIASES[team];
  if (normalized && normalized !== original) {
    report.normalizedTeamCount += 1;
  }
  return normalized ?? null;
}

function toRole(item: RawRecord, name: string): RoleDraft {
  return {
    id: cleanText(item.id) || name,
    name,
    ability: cleanText(item.ability),
    selected: true,
    setup: normalizeSetup(item.setup),
    image: cleanText(item.image),
    firstNight: parseNumber(item.firstNight),
    firstNightReminder: cleanText(item.firstNightReminder ?? item.firstReminder),
    otherNight: parseNumber(item.otherNight),
    otherNightReminder: cleanText(item.otherNightReminder ?? item.ogherNightReminder),
    reminders: toStringList(item.reminders),
    remindersGlobal: toStringList(item.remindersGlobal ?? item.reminders_global),
  };
}

function toJinx(item: RawRecord, name: string): JinxDraft {
  return {
    id: cleanText(item.id) || name,
    name,
    ability: cleanText(item.ability),
    targets: splitTargets(name),
  };
}

function collectNestedJinxes(
  script: ScriptDraft,
  item: RawRecord,
  sourceName: string,
  report: PlayCleanupReport,
) {
  if (!Array.isArray(item.jinxes)) {
    return;
  }

  for (const rawJinx of item.jinxes) {
    if (!isRecord(rawJinx)) {
      continue;
    }
    const target = cleanText(rawJinx.name ?? rawJinx.targetName ?? rawJinx.id);
    const ability = cleanText(rawJinx.ability ?? rawJinx.reason ?? rawJinx.rule);
    const name = target ? `${sourceName} & ${target}` : sourceName;
    script.jinxes.push({
      id: `${cleanText(item.id) || sourceName}:${cleanText(rawJinx.id) || target || report.jinxCount}`,
      name,
      ability,
      targets: target ? [sourceName, target] : [sourceName],
    });
    report.jinxCount += 1;
  }
}

function normalizeSetup(value: unknown): 0 | 1 {
  if (value === true) {
    return 1;
  }
  if (value === false || value === null || value === undefined) {
    return 0;
  }
  const raw = cleanText(value).toLowerCase();
  if (!raw || raw === "false" || raw === "null" || raw === "none" || raw === "no") {
    return 0;
  }
  if (raw === "true" || raw === "yes") {
    return 1;
  }
  return parseNumber(raw) !== 0 ? 1 : 0;
}

function hasNightOrder(value: unknown) {
  return parseNumber(value) !== 0;
}

function parseNumber(value: unknown) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean);
  }
  const raw = cleanText(value);
  if (!raw) {
    return [];
  }
  return raw.split("||").map(cleanText).filter(Boolean);
}

function splitTargets(name: string): string[] {
  return name.includes("&") ? name.split("&").map(cleanText).filter(Boolean) : [];
}

function cleanText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).replace(/\s+/g, " ").trim();
}

function isRecord(value: unknown): value is RawRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
