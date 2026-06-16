import type { JinxDraft } from "../types";

export type JinxLibrarySource = "custom" | "database";

export interface JinxIndexItem {
  id: string;
  name: string;
  team: "jinx";
  totalOccurrenceCount?: number;
  fileName?: string;
}

export interface JinxIndex {
  source: string;
  jinxCount: number;
  totalOccurrenceCount: number;
  jinxes: JinxIndexItem[];
}

export interface JinxVariants {
  ability: string[];
}

export interface JinxRecord {
  id: string;
  name: string;
  team: "jinx";
  targets: string[];
  totalOccurrenceCount: number;
  fileName?: string;
  targetDetectionNotes: string[];
  issueNotes: string[];
  variants: JinxVariants;
}

export interface JinxLibraryEntry {
  source: JinxLibrarySource;
  loaded: boolean;
  record: JinxRecord;
}

interface RawRecord {
  [key: string]: unknown;
}

const databaseEntryCache = new Map<string, JinxLibraryEntry[]>();

export async function loadJinxLibrary() {
  const [custom, database] = await Promise.all([
    loadJinxRecords("/custom/jinxes", "custom", false),
    loadJinxRecords("/jinxes", "database", false),
  ]);
  const customNames = new Set(custom.map((entry) => entry.record.name));

  return {
    custom,
    database: database.filter((entry) => !customNames.has(entry.record.name)),
  };
}

export async function loadJinxEntryRecord(entry: JinxLibraryEntry) {
  if (entry.loaded) {
    return entry;
  }

  const fileName = entry.record.fileName || safeJinxFileName(entry.record.name);
  const record = await fetchJinxRecord(entry.source, fileName, entry.record.name);
  if (!record) {
    return entry;
  }

  const rawRecord = record as RawRecord;
  return {
    source: entry.source,
    loaded: true,
    record: normalizeJinxRecord({
      ...rawRecord,
      fileName,
      totalOccurrenceCount: toNumber(rawRecord.totalOccurrenceCount, entry.record.totalOccurrenceCount || 1),
    }),
  } satisfies JinxLibraryEntry;
}

export async function saveJinxRecord(source: JinxLibrarySource, record: JinxRecord) {
  const normalized = normalizeJinxRecord({
    ...record,
    fileName: record.fileName || safeJinxFileName(record.name),
    totalOccurrenceCount: Math.max(1, record.totalOccurrenceCount || 1),
  });
  const body = {
    source,
    fileName: normalized.fileName,
    record: jinxRecordForStorage(normalized),
  };

  if (preferTauriStorage()) {
    const tauriSaved = await saveJinxRecordWithTauri(body);
    if (tauriSaved) {
      invalidateJinxCache();
      return tauriSaved;
    }
  }

  const viteSaved = await saveJinxRecordWithVite(body);
  if (viteSaved) {
    invalidateJinxCache();
    return viteSaved;
  }

  const tauriSaved = await saveJinxRecordWithTauri(body);
  if (tauriSaved) {
    invalidateJinxCache();
    return tauriSaved;
  }

  throw new Error("无法保存相克规则。");
}

export async function deleteJinxRecord(entry: JinxLibraryEntry) {
  const payload = {
    source: entry.source,
    fileName: entry.record.fileName || safeJinxFileName(entry.record.name),
    name: entry.record.name,
  };
  const errors: string[] = [];

  if (preferTauriStorage()) {
    const tauriDeleted = await deleteJinxRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      invalidateJinxCache();
      return true;
    }
  }

  const viteDeleted = await deleteJinxRecordWithVite(payload, errors);
  if (viteDeleted) {
    invalidateJinxCache();
    return true;
  }

  if (!preferTauriStorage()) {
    const tauriDeleted = await deleteJinxRecordWithTauri(payload, errors);
    if (tauriDeleted) {
      invalidateJinxCache();
      return true;
    }
  }

  throw new Error(`无法删除这个相克规则。${errors.length ? ` ${errors.join("；")}` : ""}`);
}

export function mergeJinxRecordVariants(base: JinxRecord, addition: JinxRecord) {
  const normalizedBase = normalizeJinxRecord(base);
  const normalizedAddition = normalizeJinxRecord(addition);

  return normalizeJinxRecord({
    ...normalizedBase,
    id: normalizedAddition.id || normalizedBase.id,
    name: normalizedAddition.name || normalizedBase.name,
    targets: normalizedAddition.targets.length ? normalizedAddition.targets : normalizedBase.targets,
    totalOccurrenceCount: Math.max(normalizedBase.totalOccurrenceCount, normalizedAddition.totalOccurrenceCount, 1),
    targetDetectionNotes: normalizedAddition.targets.length
      ? normalizedAddition.targetDetectionNotes
      : mergePrimitiveVariants(normalizedBase.targetDetectionNotes, normalizedAddition.targetDetectionNotes),
    issueNotes: mergePrimitiveVariants(normalizedBase.issueNotes, normalizedAddition.issueNotes),
    variants: {
      ability: mergePrimitiveVariants(normalizedBase.variants.ability, normalizedAddition.variants.ability),
    },
  });
}

async function fetchJinxRecord(source: JinxLibrarySource, fileName: string, name: string) {
  const candidates = [
    fileName,
    safeJinxFileName(name),
    `${name}.json`,
  ];
  const basePath = source === "custom" ? "/custom/jinxes" : "/jinxes";
  const seen = new Set<string>();
  for (const candidate of candidates) {
    if (!candidate || seen.has(candidate)) {
      continue;
    }
    seen.add(candidate);
    const record = await fetchJson<unknown>(jinxFileUrl(basePath, candidate));
    if (record) {
      return record;
    }
  }
  return null;
}

export async function loadMatchingJinxRecords(characterNames: string[]) {
  const playNames = new Set(characterNames.map(cleanText).filter(Boolean));
  if (!playNames.size) {
    return [];
  }

  const library = await loadJinxLibrary();
  const entries = [...library.custom, ...library.database];
  const matchingEntries = entries.filter((entry) => {
    const targets = targetsFromName(entry.record.name);
    return targetsMatchPlay(targets, playNames);
  });

  const loadedEntries = await Promise.all(matchingEntries.map(loadJinxEntryRecord));
  return loadedEntries
    .map((entry) => entry.record)
    .filter((record) =>
      targetsMatchPlay(record.targets, playNames) ||
      targetsMatchPlay(targetsFromName(record.name), playNames),
    );
}

export function jinxRecordMatchesPlay(record: JinxRecord, characterNames: string[]) {
  const playNames = new Set(characterNames.map(cleanText).filter(Boolean));
  if (!playNames.size) {
    return false;
  }

  return targetsMatchPlay(record.targets, playNames) || targetsMatchPlay(targetsFromName(record.name), playNames);
}

export function jinxRecordToDraft(record: JinxRecord): JinxDraft {
  return {
    id: crypto.randomUUID(),
    name: record.name,
    ability: firstVariant(record.variants.ability, ""),
    included: true,
    targets: record.targets,
  };
}

export function draftToJinxRecord(draft: JinxDraft): JinxRecord {
  return normalizeJinxRecord({
    id: draft.name,
    name: draft.name,
    team: "jinx",
    targets: draft.targets,
    totalOccurrenceCount: 1,
    targetDetectionNotes: [],
    issueNotes: [],
    variants: {
      ability: [draft.ability ?? ""],
    },
  });
}

export function normalizeJinxRecord(input: unknown): JinxRecord {
  const record = isRecord(input) ? input : {};
  const name = cleanText(record.name) || "未命名相克规则";
  const variants = isRecord(record.variants) ? record.variants : {};
  const targets = toStringArray(record.targets);
  const normalizedTargets = targets.length ? targets : targetsFromName(name);

  return {
    id: cleanText(record.id) || name,
    name,
    team: "jinx",
    targets: normalizedTargets,
    totalOccurrenceCount: toNumber(record.totalOccurrenceCount, 1),
    fileName: cleanText(record.fileName) || safeJinxFileName(name),
    targetDetectionNotes: toStringArray(record.targetDetectionNotes),
    issueNotes: toStringArray(record.issueNotes),
    variants: {
      ability: toStringVariants(variants.ability ?? record.ability),
    },
  };
}

export function jinxRecordForStorage(record: JinxRecord) {
  const normalized = normalizeJinxRecord(record);
  return {
    id: normalized.id,
    name: normalized.name,
    team: "jinx" as const,
    targets: normalized.targets,
    targetDetectionNotes: normalized.targetDetectionNotes,
    issueNotes: normalized.issueNotes,
    totalOccurrenceCount: normalized.totalOccurrenceCount,
    variants: {
      ability: normalized.variants.ability,
    },
  };
}

export function targetsFromName(name: string) {
  return name
    .split(/[&＆]/u)
    .map(cleanText)
    .filter(Boolean);
}

function targetsMatchPlay(targets: string[], playNames: Set<string>) {
  const canonicalTargets = Array.from(
    new Set(targets.map((target) => canonicalTargetName(target, playNames)).filter(Boolean)),
  );
  return canonicalTargets.length > 0 && canonicalTargets.every((target) => playNames.has(target));
}

function canonicalTargetName(target: string, playNames: Set<string>) {
  const cleanTarget = cleanText(target);
  if (!cleanTarget || playNames.has(cleanTarget)) {
    return cleanTarget;
  }

  const parts = cleanTarget.split("：").map(cleanText).filter(Boolean);
  for (let index = parts.length - 1; index > 0; index -= 1) {
    const suffix = parts.slice(index).join("：");
    if (playNames.has(suffix)) {
      return suffix;
    }
  }
  return cleanTarget;
}

export function safeJinxFileName(name: string) {
  const withoutExtension = name.endsWith(".json") ? name.slice(0, -5) : name;
  const safeName = withoutExtension
    .trim()
    .replace(/\s+/gu, "_")
    .replace(/\\/gu, "＼")
    .replace(/\//gu, "／")
    .replace(/:/gu, "：")
    .replace(/\*/gu, "＊")
    .replace(/\?/gu, "？")
    .replace(/"/gu, "＂")
    .replace(/</gu, "＜")
    .replace(/>/gu, "＞")
    .replace(/\|/gu, "｜");
  return `${safeName || "未命名相克规则"}.json`;
}

function jinxFileUrl(basePath: string, fileName: string) {
  return `${basePath}/${fileName
    .replace(/%/gu, "%25")
    .replace(/#/gu, "%23")}`;
}

export function firstVariant<T>(values: T[] | undefined, fallback: T): T {
  return values && values.length > 0 ? values[0] : fallback;
}

function recordFromIndexItem(item: JinxIndexItem): JinxRecord {
  return normalizeJinxRecord({
    id: item.id,
    name: item.name,
    team: "jinx",
    totalOccurrenceCount: item.totalOccurrenceCount || 1,
    fileName: item.fileName || safeJinxFileName(item.name),
    targets: targetsFromName(item.name),
    targetDetectionNotes: [],
    issueNotes: [],
    variants: {
      ability: [""],
    },
  });
}

function cloneEntry(entry: JinxLibraryEntry): JinxLibraryEntry {
  return {
    source: entry.source,
    loaded: entry.loaded,
    record: normalizeJinxRecord(entry.record),
  };
}

function sortEntries(left: JinxLibraryEntry, right: JinxLibraryEntry) {
  return right.record.totalOccurrenceCount - left.record.totalOccurrenceCount ||
    left.record.name.localeCompare(right.record.name, "zh-Hans-CN");
}

async function fetchJinxIndex(url: string) {
  const index = await fetchJson<unknown>(url);
  if (!isRecord(index) || !Array.isArray(index.jinxes)) {
    return null;
  }

  return {
    source: cleanText(index.source) || "jinxes",
    jinxCount: toNumber(index.jinxCount, index.jinxes.length),
    totalOccurrenceCount: toNumber(index.totalOccurrenceCount, 0),
    jinxes: index.jinxes
      .filter(isRecord)
      .map((item) => ({
        id: cleanText(item.id) || cleanText(item.name),
        name: cleanText(item.name) || cleanText(item.id),
        team: "jinx" as const,
        totalOccurrenceCount: toNumber(item.totalOccurrenceCount, 1),
        fileName: cleanText(item.fileName),
      }))
      .filter((item) => item.name),
  } satisfies JinxIndex;
}

async function loadJinxRecords(
  basePath: string,
  source: JinxLibrarySource,
  loadRecords: boolean,
): Promise<JinxLibraryEntry[]> {
  if (source === "database" && !loadRecords) {
    const cached = databaseEntryCache.get("database");
    if (cached) {
      return cached.map(cloneEntry);
    }
  }

  const index = await fetchJinxIndex(`${basePath}/index.json`);
  if (!index) {
    return [];
  }

  if (!loadRecords) {
    const entries = index.jinxes
      .map((item) => ({
        source,
        loaded: false,
        record: recordFromIndexItem(item),
      }))
      .sort(sortEntries);
    if (source === "database") {
      databaseEntryCache.set("database", entries.map(cloneEntry));
    }
    return entries;
  }

  const records = await Promise.all(
    index.jinxes.map(async (item) => {
      const fileName = item.fileName || safeJinxFileName(item.name);
      const record = await fetchJinxRecord(source, fileName, item.name);
      if (!record) {
        return null;
      }
      const rawRecord = record as RawRecord;
      return {
        source,
        loaded: true,
        record: normalizeJinxRecord({
          ...rawRecord,
          fileName,
          totalOccurrenceCount: toNumber(rawRecord.totalOccurrenceCount, item.totalOccurrenceCount || 1),
        }),
      };
    }),
  );

  return records
    .filter((entry): entry is JinxLibraryEntry => Boolean(entry))
    .sort(sortEntries);
}

function invalidateJinxCache() {
  databaseEntryCache.delete("database");
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

async function saveJinxRecordWithVite(
  body: { source: JinxLibrarySource; fileName?: string; record: unknown },
) {
  try {
    const response = await fetch("/__jinx_record", {
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
    return normalizeJinxRecord(result.record ?? body.record);
  } catch {
    return null;
  }
}

async function saveJinxRecordWithTauri(
  body: { source: JinxLibrarySource; fileName?: string; record: unknown },
) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const saved = await invoke<unknown>("save_jinx", {
      source: body.source,
      fileName: body.fileName,
      file_name: body.fileName,
      recordJson: JSON.stringify(body.record, null, 2),
      record_json: JSON.stringify(body.record, null, 2),
    });
    return normalizeJinxRecord(saved);
  } catch (error) {
    console.warn("Tauri 保存相克规则失败。", error);
    return null;
  }
}

async function deleteJinxRecordWithVite(
  body: { source: JinxLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const response = await fetch("/__jinx_record", {
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

async function deleteJinxRecordWithTauri(
  body: { source: JinxLibrarySource; fileName?: string; name: string },
  errors: string[] = [],
) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("delete_jinx", {
      source: body.source,
      fileName: body.fileName,
      file_name: body.fileName,
      name: body.name,
    });
    return true;
  } catch (error) {
    errors.push(`Tauri: ${error instanceof Error ? error.message : String(error)}`);
    console.warn("Tauri 删除相克规则失败。", error);
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

function toStringVariants(value: unknown) {
  const values = Array.isArray(value) ? value.map(cleanText) : [cleanText(value)];
  const filtered = values.filter((item, index) => item || index === 0);
  return filtered.length ? filtered : [""];
}

function mergePrimitiveVariants<T>(base: T[], addition: T[]) {
  const seen = new Set<string>();
  const merged: T[] = [];

  for (const value of [...base, ...addition]) {
    const key = JSON.stringify(value);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(value);
  }

  return merged;
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

function toNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cleanText(value: unknown) {
  return value === null || value === undefined ? "" : String(value).replace(/\s+/gu, " ").trim();
}

function isRecord(value: unknown): value is RawRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
