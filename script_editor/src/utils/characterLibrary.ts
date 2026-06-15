import type { RoleDraft, TeamKey } from "../types";

export type CharacterLibrarySource = "custom" | "database";

export interface CharacterIndexItem {
  id: string;
  name: string;
  team: TeamKey;
  totalOccurrenceCount?: number;
  fileName?: string;
}

export interface CharacterIndex {
  team: TeamKey;
  folder: string;
  characterCount: number;
  totalOccurrenceCount: number;
  characters: CharacterIndexItem[];
}

export interface CharacterVariants {
  ability: string[];
  image: string[];
  firstNight: number[];
  firstNightReminder: string[];
  otherNight: number[];
  otherNightReminder: string[];
  reminders: string[][];
  remindersGlobal: string[][];
  setup: Array<0 | 1>;
  flavor: string[];
}

export interface CharacterRecord {
  id: string;
  name: string;
  team: TeamKey;
  totalOccurrenceCount: number;
  notes: string[];
  fileName?: string;
  variants: CharacterVariants;
}

export interface CharacterLibraryEntry {
  source: CharacterLibrarySource;
  loaded: boolean;
  record: CharacterRecord;
}

interface RawRecord {
  [key: string]: unknown;
}

export const characterTeamFolders: Record<TeamKey, string> = {
  townsfolk: "townsfolks",
  outsider: "outsiders",
  minion: "minions",
  demon: "demons",
  traveler: "travelers",
};

export async function loadCharacterLibrary(team: TeamKey) {
  const [custom, database] = await Promise.all([
    loadCharacterRecords(`/custom/${characterTeamFolders[team]}`, "custom", team, true),
    loadCharacterRecords(`/characters/${characterTeamFolders[team]}`, "database", team, false),
  ]);

  return {
    custom,
    database,
  };
}

export async function loadCharacterEntryRecord(entry: CharacterLibraryEntry) {
  if (entry.loaded) {
    return entry;
  }

  const fileName = entry.record.fileName || safeCustomCharacterFileName(entry.record.name);
  const record = await fetchJson<unknown>(
    `/characters/${characterTeamFolders[entry.record.team]}/${encodeURIComponent(fileName)}`,
  );
  if (!record) {
    return entry;
  }

  const rawRecord = record as RawRecord;
  return {
    ...entry,
    loaded: true,
    record: normalizeCharacterRecord({
      ...rawRecord,
      fileName,
      team: entry.record.team,
      totalOccurrenceCount: toNumber(rawRecord.totalOccurrenceCount, entry.record.totalOccurrenceCount || 1),
    }, entry.record.team),
  } satisfies CharacterLibraryEntry;
}

export async function saveCustomCharacterRecord(team: TeamKey, record: CharacterRecord) {
  const normalized = normalizeCharacterRecord({
    ...record,
    team,
    fileName: safeCustomCharacterFileName(record.name),
    totalOccurrenceCount: Math.max(1, record.totalOccurrenceCount || 1),
  }, team);
  const body = {
    team,
    fileName: normalized.fileName,
    record: normalized,
  };

  if (preferTauriStorage()) {
    const tauriSaved = await saveCustomCharacterRecordWithTauri(body);
    if (tauriSaved) {
      return tauriSaved;
    }
  }

  const viteSaved = await saveCustomCharacterRecordWithVite(body);
  if (viteSaved) {
    return viteSaved;
  }

  const tauriSaved = await saveCustomCharacterRecordWithTauri(body);
  if (tauriSaved) {
    return tauriSaved;
  }

  throw new Error("无法保存自定义角色。");
}

export async function deleteCharacterRecord(entry: CharacterLibraryEntry) {
  const payload = {
    team: entry.record.team,
    source: entry.source,
    fileName: entry.record.fileName || safeCustomCharacterFileName(entry.record.name),
    name: entry.record.name,
  };
  const errors: string[] = [];

  if (preferTauriStorage()) {
    const tauriDeleted = await deleteCharacterRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      return true;
    }
  }

  const viteDeleted = await deleteCharacterRecordWithVite(payload, errors);
  if (viteDeleted) {
    return true;
  }

  if (!preferTauriStorage()) {
    const tauriDeleted = await deleteCharacterRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      return true;
    }
  }

  throw new Error(`无法删除这个角色。${errors.length ? ` ${errors.join("；")}` : ""}`);
}

export function mergeCharacterRecordVariants(base: CharacterRecord, addition: CharacterRecord) {
  const normalizedBase = normalizeCharacterRecord(base, base.team);
  const normalizedAddition = normalizeCharacterRecord(addition, addition.team);

  return normalizeCharacterRecord({
    ...normalizedBase,
    id: normalizedAddition.id || normalizedBase.id,
    name: normalizedAddition.name || normalizedBase.name,
    totalOccurrenceCount: Math.max(normalizedBase.totalOccurrenceCount, normalizedAddition.totalOccurrenceCount, 1),
    variants: {
      ability: mergePrimitiveVariants(normalizedBase.variants.ability, normalizedAddition.variants.ability),
      image: mergePrimitiveVariants(normalizedBase.variants.image, normalizedAddition.variants.image),
      firstNight: mergePrimitiveVariants(normalizedBase.variants.firstNight, normalizedAddition.variants.firstNight),
      firstNightReminder: mergePrimitiveVariants(
        normalizedBase.variants.firstNightReminder,
        normalizedAddition.variants.firstNightReminder,
      ),
      otherNight: mergePrimitiveVariants(normalizedBase.variants.otherNight, normalizedAddition.variants.otherNight),
      otherNightReminder: mergePrimitiveVariants(
        normalizedBase.variants.otherNightReminder,
        normalizedAddition.variants.otherNightReminder,
      ),
      reminders: mergeListVariants(normalizedBase.variants.reminders, normalizedAddition.variants.reminders),
      remindersGlobal: mergeListVariants(
        normalizedBase.variants.remindersGlobal,
        normalizedAddition.variants.remindersGlobal,
      ),
      setup: mergePrimitiveVariants(normalizedBase.variants.setup, normalizedAddition.variants.setup),
      flavor: mergePrimitiveVariants(normalizedBase.variants.flavor, normalizedAddition.variants.flavor),
    },
  }, normalizedAddition.team);
}

export function characterRecordToDraft(record: CharacterRecord): RoleDraft {
  return {
    id: crypto.randomUUID(),
    name: record.name,
    ability: firstVariant(record.variants.ability, ""),
    image: firstVariant(record.variants.image, ""),
    selected: true,
    firstNight: firstVariant(record.variants.firstNight, 0),
    firstNightReminder: firstVariant(record.variants.firstNightReminder, ""),
    otherNight: firstVariant(record.variants.otherNight, 0),
    otherNightReminder: firstVariant(record.variants.otherNightReminder, ""),
    reminders: firstVariant(record.variants.reminders, []),
    remindersGlobal: firstVariant(record.variants.remindersGlobal, []),
    setup: firstVariant(record.variants.setup, 0),
    flavor: firstVariant(record.variants.flavor, ""),
  };
}

export function firstCharacterImage(record: CharacterRecord) {
  return firstVariant(record.variants.image, "");
}

export function firstVariant<T>(values: T[] | undefined, fallback: T): T {
  return values && values.length > 0 ? values[0] : fallback;
}

export function safeCustomCharacterFileName(name: string) {
  return `${name.trim().replace(/[\\/:*?"<>|]+/g, "_") || "未命名角色"}.json`;
}

export function normalizeCharacterRecord(input: unknown, team: TeamKey): CharacterRecord {
  const record = isRecord(input) ? input : {};
  const name = cleanText(record.name) || "未命名角色";
  const variants = isRecord(record.variants) ? record.variants : {};

  return {
    id: cleanText(record.id) || name,
    name,
    team,
    totalOccurrenceCount: toNumber(record.totalOccurrenceCount, 1),
    notes: toStringArray(record.notes),
    fileName: cleanText(record.fileName) || safeCustomCharacterFileName(name),
    variants: {
      ability: toStringVariants(variants.ability),
      image: toStringVariants(variants.image),
      firstNight: toNumberVariants(variants.firstNight),
      firstNightReminder: toStringVariants(variants.firstNightReminder),
      otherNight: toNumberVariants(variants.otherNight),
      otherNightReminder: toStringVariants(variants.otherNightReminder),
      reminders: toStringListVariants(variants.reminders),
      remindersGlobal: toStringListVariants(variants.remindersGlobal),
      setup: toSetupVariants(variants.setup),
      flavor: toStringVariants(variants.flavor),
    },
  };
}

async function loadCharacterRecords(
  basePath: string,
  source: CharacterLibrarySource,
  team: TeamKey,
  loadRecords: boolean,
): Promise<CharacterLibraryEntry[]> {
  const index = await fetchCharacterIndex(`${basePath}/index.json`, team);
  if (!index) {
    return [];
  }

  if (!loadRecords) {
    return index.characters
      .map((item) => ({
        source,
        loaded: false,
        record: recordFromIndexItem(item, team),
      }))
      .sort(sortEntries);
  }

  const records = await Promise.all(
    index.characters.map(async (item) => {
      const fileName = item.fileName || safeCustomCharacterFileName(item.name);
      const record = await fetchJson<unknown>(`${basePath}/${encodeURIComponent(fileName)}`);
      if (!record) {
        return null;
      }
      const rawRecord = record as RawRecord;
      return {
        source,
        loaded: true,
        record: normalizeCharacterRecord({
          ...rawRecord,
          fileName,
          team,
          totalOccurrenceCount: toNumber(rawRecord.totalOccurrenceCount, item.totalOccurrenceCount || 1),
        }, team),
      };
    }),
  );

  return records
    .filter((entry): entry is CharacterLibraryEntry => Boolean(entry))
    .sort(sortEntries);
}

function recordFromIndexItem(item: CharacterIndexItem, team: TeamKey): CharacterRecord {
  return normalizeCharacterRecord({
    id: item.id,
    name: item.name,
    team,
    totalOccurrenceCount: item.totalOccurrenceCount || 1,
    fileName: item.fileName || safeCustomCharacterFileName(item.name),
    notes: [],
    variants: {
      ability: [""],
      image: [""],
      firstNight: [0],
      firstNightReminder: [""],
      otherNight: [0],
      otherNightReminder: [""],
      reminders: [[]],
      remindersGlobal: [[]],
      setup: [0],
      flavor: [""],
    },
  }, team);
}

function sortEntries(left: CharacterLibraryEntry, right: CharacterLibraryEntry) {
  return right.record.totalOccurrenceCount - left.record.totalOccurrenceCount ||
    left.record.name.localeCompare(right.record.name, "zh-Hans-CN");
}

async function fetchCharacterIndex(url: string, team: TeamKey) {
  const index = await fetchJson<unknown>(url);
  if (!isRecord(index) || !Array.isArray(index.characters)) {
    return null;
  }

  return {
    team,
    folder: cleanText(index.folder) || characterTeamFolders[team],
    characterCount: toNumber(index.characterCount, index.characters.length),
    totalOccurrenceCount: toNumber(index.totalOccurrenceCount, 0),
    characters: index.characters
      .filter(isRecord)
      .map((item) => ({
        id: cleanText(item.id) || cleanText(item.name),
        name: cleanText(item.name) || cleanText(item.id),
        team,
        totalOccurrenceCount: toNumber(item.totalOccurrenceCount, 1),
        fileName: cleanText(item.fileName),
      }))
      .filter((item) => item.name),
  } satisfies CharacterIndex;
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(`${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}`);
    if (!response.ok) {
      return null;
    }
    return await response.json() as T;
  } catch {
    return null;
  }
}

async function saveCustomCharacterRecordWithVite(body: { team: TeamKey; fileName?: string; record: CharacterRecord }) {
  try {
    const response = await fetch("/__custom_character", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      return null;
    }
    const result = await response.json() as { record?: unknown };
    return normalizeCharacterRecord(result.record ?? body.record, body.team);
  } catch {
    return null;
  }
}

async function saveCustomCharacterRecordWithTauri(body: { team: TeamKey; fileName?: string; record: CharacterRecord }) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const saved = await invoke<unknown>("save_custom_character", {
      team: body.team,
      fileName: body.fileName,
      file_name: body.fileName,
      recordJson: JSON.stringify(body.record, null, 2),
      record_json: JSON.stringify(body.record, null, 2),
    });
    return normalizeCharacterRecord(saved, body.team);
  } catch (error) {
    console.warn("Tauri 保存角色失败。", error);
    return null;
  }
}

async function deleteCharacterRecordWithVite(
  body: { team: TeamKey; source: CharacterLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const response = await fetch("/__character_record", {
      method: "DELETE",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      errors.push(`Vite: ${response.status} ${await response.text()}`);
      return false;
    }
    return true;
  } catch (error) {
    errors.push(`Vite: ${error instanceof Error ? error.message : String(error)}`);
    return false;
  }
}

async function deleteCharacterRecordWithTauri(
  body: { team: TeamKey; source: CharacterLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("delete_character", {
      team: body.team,
      source: body.source,
      fileName: body.fileName,
      file_name: body.fileName,
      name: body.name,
    });
    return true;
  } catch (error) {
    errors.push(`Tauri: ${error instanceof Error ? error.message : String(error)}`);
    console.warn("Tauri 删除角色失败。", error);
    return false;
  }
}

function isTauriRuntime() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function preferTauriStorage() {
  return isTauriRuntime() && !isLocalDevServer();
}

function isLocalDevServer() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.location.protocol === "http:" || window.location.protocol === "https:";
}

function mergePrimitiveVariants<T>(base: T[], addition: T[]) {
  return mergeByKey(base, addition, (value) => JSON.stringify(value));
}

function mergeListVariants(base: string[][], addition: string[][]) {
  return mergeByKey(base, addition, (value) => JSON.stringify(value));
}

function mergeByKey<T>(base: T[], addition: T[], keyForValue: (value: T) => string) {
  const seen = new Set<string>();
  const merged: T[] = [];

  for (const value of [...base, ...addition]) {
    const key = keyForValue(value);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(value);
  }

  return merged;
}

function toStringVariants(value: unknown) {
  const values = Array.isArray(value) ? value.map(cleanText) : [cleanText(value)];
  const filtered = values.filter((item, index) => item || index === 0);
  return filtered.length ? filtered : [""];
}

function toNumberVariants(value: unknown) {
  const values = Array.isArray(value) ? value.map((item) => toNumber(item, 0)) : [toNumber(value, 0)];
  return values.length ? values : [0];
}

function toSetupVariants(value: unknown): Array<0 | 1> {
  const values = Array.isArray(value) ? value.map(toSetup) : [toSetup(value)];
  return values.length ? values : [0];
}

function toStringListVariants(value: unknown) {
  if (!Array.isArray(value)) {
    return [toStringArray(value)];
  }
  if (!value.length) {
    return [[]];
  }
  return value.map(toStringArray);
}

function toStringArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean);
  }
  return cleanText(value)
    .split("||")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toSetup(value: unknown): 0 | 1 {
  if (value === true) {
    return 1;
  }
  if (value === false || value === null || value === undefined) {
    return 0;
  }
  const parsed = cleanText(value).toLowerCase();
  return parsed === "true" || parsed === "yes" || toNumber(parsed, 0) !== 0 ? 1 : 0;
}

function toNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cleanText(value: unknown) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function isRecord(value: unknown): value is RawRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
