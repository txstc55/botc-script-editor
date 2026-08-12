type RawRecord = Record<string, unknown>;
type DatabaseTeam = "townsfolk" | "outsider" | "minion" | "demon" | "traveler" | "fabled";

interface RoleIdMapEntry {
  name: string;
  team: DatabaseTeam;
  fileName: string;
}

interface RoleIdMap {
  exact: Record<string, RoleIdMapEntry>;
  normalized: Record<string, RoleIdMapEntry>;
}

const teamFolders: Record<DatabaseTeam, string> = {
  townsfolk: "townsfolks",
  outsider: "outsiders",
  minion: "minions",
  demon: "demons",
  traveler: "travelers",
  fabled: "fabled",
};

let roleIdMapPromise: Promise<RoleIdMap | null> | null = null;
const roleRecordPromises = new Map<string, Promise<RawRecord | null>>();

export async function hydratePlayRoleIds(input: unknown): Promise<unknown> {
  if (!Array.isArray(input) || !input.some(isIdOnlyRole)) {
    return input;
  }

  const idMap = await loadRoleIdMap();
  if (!idMap) {
    return input;
  }

  return await Promise.all(input.map(async (item) => {
    if (!isIdOnlyRole(item)) {
      return item;
    }
    const rawId = cleanText(item.id);
    const mapped = idMap.exact[rawId] ?? idMap.normalized[normalizeAlias(rawId)];
    if (!mapped) {
      return item;
    }
    const record = await loadRoleRecord(mapped);
    return record ? { ...recordToPlayItem(record, mapped), ...item, id: rawId } : item;
  }));
}

function isIdOnlyRole(value: unknown): value is RawRecord {
  return isRecord(value) && cleanText(value.id) !== "_meta" && Boolean(cleanText(value.id)) &&
    !cleanText(value.name) && !cleanText(value.team);
}

async function loadRoleIdMap() {
  roleIdMapPromise ??= fetchJson<RoleIdMap>("/characters/id-map.json");
  return await roleIdMapPromise;
}

async function loadRoleRecord(entry: RoleIdMapEntry) {
  const path = `/characters/${teamFolders[entry.team]}/${encodeURIComponent(entry.fileName)}`;
  let promise = roleRecordPromises.get(path);
  if (!promise) {
    promise = fetchJson<RawRecord>(path);
    roleRecordPromises.set(path, promise);
  }
  return await promise;
}

function recordToPlayItem(record: RawRecord, mapped: RoleIdMapEntry): RawRecord {
  const variants = isRecord(record.variants) ? record.variants : {};
  return {
    name: cleanText(record.name) || mapped.name,
    team: cleanText(record.team) || mapped.team,
    ability: firstVariant(variants.ability, ""),
    image: firstVariant(variants.image, ""),
    firstNight: firstVariant(variants.firstNight, 0),
    firstNightReminder: firstVariant(variants.firstNightReminder, ""),
    otherNight: firstVariant(variants.otherNight, 0),
    otherNightReminder: firstVariant(variants.otherNightReminder, ""),
    reminders: firstVariant(variants.reminders, []),
    remindersGlobal: firstVariant(variants.remindersGlobal, []),
    setup: firstVariant(variants.setup, 0),
    flavor: firstVariant(variants.flavor, ""),
  };
}

function firstVariant(value: unknown, fallback: unknown) {
  return Array.isArray(value) && value.length ? value[0] : fallback;
}

function normalizeAlias(value: string) {
  return value.normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(path);
    return response.ok ? await response.json() as T : null;
  } catch {
    return null;
  }
}

function cleanText(value: unknown) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function isRecord(value: unknown): value is RawRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
