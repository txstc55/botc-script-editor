import type { FabledDraft } from "../types";

export type FabledLibrarySource = "custom" | "database";

export interface FabledIndexItem {
  id: string;
  name: string;
  team: "fabled";
  totalOccurrenceCount?: number;
  fileName?: string;
}

export interface FabledIndex {
  team: "fabled";
  folder: string;
  characterCount: number;
  totalOccurrenceCount: number;
  characters: FabledIndexItem[];
}

export interface FabledVariants {
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

export interface FabledRecord {
  id: string;
  name: string;
  team: "fabled";
  totalOccurrenceCount: number;
  notes: string[];
  fileName?: string;
  variants: FabledVariants;
}

export interface FabledLibraryEntry {
  source: FabledLibrarySource;
  record: FabledRecord;
}

interface RawRecord {
  [key: string]: unknown;
}

export async function loadFabledLibrary() {
  const [custom, database] = await Promise.all([
    loadFabledRecords("/custom/fabled", "custom"),
    loadFabledRecords("/characters/fabled", "database"),
  ]);
  const customNames = new Set(custom.map((entry) => entry.record.name));

  return {
    custom,
    database: database.filter((entry) => !customNames.has(entry.record.name)),
  };
}

export async function saveCustomFabledRecord(record: FabledRecord) {
  return saveFabledRecord("custom", record);
}

export async function saveFabledRecord(source: FabledLibrarySource, record: FabledRecord) {
  const normalized = normalizeFabledRecord({
    ...record,
    fileName: record.fileName || safeCustomFabledFileName(record.name),
    totalOccurrenceCount: Math.max(1, record.totalOccurrenceCount || 1),
  });
  const body = {
    source,
    fileName: normalized.fileName,
    record: normalized,
  };

  if (preferTauriStorage()) {
    const tauriSaved = await saveFabledRecordWithTauri(body);
    if (tauriSaved) {
      return tauriSaved;
    }
  }

  const viteSaved = await saveFabledRecordWithVite(body);
  if (viteSaved) {
    return viteSaved;
  }

  const tauriSaved = await saveFabledRecordWithTauri(body);
  if (tauriSaved) {
    return tauriSaved;
  }

  throw new Error("无法保存传奇角色。");
}

export async function deleteFabledRecord(entry: FabledLibraryEntry) {
  const payload = {
    source: entry.source,
    fileName: entry.record.fileName || safeCustomFabledFileName(entry.record.name),
    name: entry.record.name,
  };
  const errors: string[] = [];

  if (preferTauriStorage()) {
    const tauriDeleted = await deleteFabledRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      return true;
    }
  }

  const viteDeleted = await deleteFabledRecordWithVite(payload, errors);
  if (viteDeleted) {
    return true;
  }

  if (!preferTauriStorage()) {
    const tauriDeleted = await deleteFabledRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      return true;
    }
  }

  throw new Error(`无法删除这个传奇角色。${errors.length ? ` ${errors.join("；")}` : ""}`);
}

export function mergeFabledRecordVariants(base: FabledRecord, addition: FabledRecord) {
  const normalizedBase = normalizeFabledRecord(base);
  const normalizedAddition = normalizeFabledRecord(addition);

  return normalizeFabledRecord({
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
  });
}

export function fabledRecordToDraft(record: FabledRecord): FabledDraft {
  return {
    id: crypto.randomUUID(),
    name: record.name,
    ability: firstVariant(record.variants.ability, ""),
    image: firstVariant(record.variants.image, ""),
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

export function firstFabledImage(record: FabledRecord) {
  return firstVariant(record.variants.image, "");
}

export function firstVariant<T>(values: T[] | undefined, fallback: T): T {
  return values && values.length > 0 ? values[0] : fallback;
}

export function safeCustomFabledFileName(name: string) {
  return `${name.trim().replace(/[\\/:*?"<>|]+/g, "_") || "未命名传奇角色"}.json`;
}

export function normalizeFabledRecord(input: unknown): FabledRecord {
  const record = isRecord(input) ? input : {};
  const name = cleanText(record.name) || "未命名传奇角色";
  const variants = isRecord(record.variants) ? record.variants : {};

  return {
    id: cleanText(record.id) || name,
    name,
    team: "fabled",
    totalOccurrenceCount: toNumber(record.totalOccurrenceCount, 1),
    notes: toStringArray(record.notes),
    fileName: cleanText(record.fileName) || safeCustomFabledFileName(name),
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

async function loadFabledRecords(basePath: string, source: FabledLibrarySource): Promise<FabledLibraryEntry[]> {
  const index = await fetchFabledIndex(`${basePath}/index.json`);
  if (!index) {
    return [];
  }

  const characters = source === "database"
    ? index.characters.filter((item) => (item.totalOccurrenceCount ?? 0) > 1)
    : index.characters;
  const records = await Promise.all(
    characters.map(async (item) => {
      const fileName = item.fileName || safeCustomFabledFileName(item.name);
      const record = await fetchJson<unknown>(`${basePath}/${encodeURIComponent(fileName)}`);
      if (!record) {
        return null;
      }
      const rawRecord = record as RawRecord;
      return {
        source,
        record: normalizeFabledRecord({
          ...rawRecord,
          fileName,
          totalOccurrenceCount: toNumber(rawRecord.totalOccurrenceCount, item.totalOccurrenceCount || 1),
        }),
      };
    }),
  );

  return records
    .filter((entry): entry is FabledLibraryEntry => Boolean(entry))
    .sort((left, right) =>
      right.record.totalOccurrenceCount - left.record.totalOccurrenceCount ||
      left.record.name.localeCompare(right.record.name, "zh-Hans-CN"),
    );
}

async function fetchFabledIndex(url: string) {
  const index = await fetchJson<unknown>(url);
  if (!isRecord(index) || !Array.isArray(index.characters)) {
    return null;
  }

  return {
    team: "fabled",
    folder: cleanText(index.folder) || "fabled",
    characterCount: toNumber(index.characterCount, index.characters.length),
    totalOccurrenceCount: toNumber(index.totalOccurrenceCount, 0),
    characters: index.characters
      .filter(isRecord)
      .map((item) => ({
        id: cleanText(item.id) || cleanText(item.name),
        name: cleanText(item.name) || cleanText(item.id),
        team: "fabled" as const,
        totalOccurrenceCount: toNumber(item.totalOccurrenceCount, 1),
        fileName: cleanText(item.fileName),
      }))
      .filter((item) => item.name),
  } satisfies FabledIndex;
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

async function saveFabledRecordWithVite(
  body: { source: FabledLibrarySource; fileName?: string; record: FabledRecord },
) {
  try {
    const response = await fetch("/__fabled_record", {
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
    return normalizeFabledRecord(result.record ?? body.record);
  } catch {
    return null;
  }
}

async function saveFabledRecordWithTauri(
  body: { source: FabledLibrarySource; fileName?: string; record: FabledRecord },
) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const saved = await invoke<unknown>("save_fabled_character", {
      source: body.source,
      fileName: body.fileName,
      file_name: body.fileName,
      recordJson: JSON.stringify(body.record, null, 2),
      record_json: JSON.stringify(body.record, null, 2),
    });
    return normalizeFabledRecord(saved);
  } catch (error) {
    console.warn("Tauri 保存传奇角色失败。", error);
    return null;
  }
}

async function deleteFabledRecordWithVite(
  body: { source: FabledLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const response = await fetch("/__fabled_record", {
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

async function deleteFabledRecordWithTauri(
  body: { source: FabledLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("delete_fabled_character", {
      source: body.source,
      fileName: body.fileName,
      file_name: body.fileName,
      name: body.name,
    });
    return true;
  } catch (error) {
    errors.push(`Tauri: ${error instanceof Error ? error.message : String(error)}`);
    console.warn("Tauri 删除传奇角色失败。", error);
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
