import type { FabledDraft, JinxDraft, RoleDraft, ScriptDraft, TeamKey } from "../types";

interface ExportMeta {
  id: "_meta";
  name: string;
  author: string;
  minionInfo?: number;
  demonInfo?: number;
}

interface ExportFabled {
  id: string;
  name: string;
  edition: "custom";
  team: "fabled";
  ability: string;
  image: string;
  setup: 0 | 1;
}

interface ExportCharacter {
  id: string;
  name: string;
  team: TeamKey;
  ability: string;
  image: string;
  firstNight: number;
  firstNightReminder: string;
  otherNight: number;
  otherNightReminder: string;
  reminders: string[];
  remindersGlobal: string[];
  setup: 0 | 1;
  flavor: string;
}

interface ExportJinx {
  id: string;
  team: "jinx";
  name: string;
  ability: string;
  image: string;
}

const exportTeamOrder: TeamKey[] = ["townsfolk", "outsider", "minion", "demon", "traveler"];

export type ExportScriptItem = ExportMeta | ExportFabled | ExportCharacter | ExportJinx;

export function buildExportJson(script: ScriptDraft): ExportScriptItem[] {
  const playCharacters = collectExportPlayCharacters(script);
  const exportItems: ExportScriptItem[] = [
    exportMeta(script),
    ...script.fabled.map(exportFabled),
  ];

  for (const team of exportTeamOrder) {
    exportItems.push(...script.teams[team].roles.filter((role) => role.selected).map((role) => exportRole(role, team)));
  }

  exportItems.push(...script.jinxes.filter((jinx) => jinx.included !== false).map((jinx) => exportJinx(jinx, playCharacters)));
  return exportItems;
}

function exportMeta(script: ScriptDraft): ExportMeta {
  const meta: ExportMeta = {
    id: "_meta",
    name: cleanText(script.name),
    author: cleanText(script.author),
  };

  if (script.builtInFirstNightEnabled.minionInfo) {
    meta.minionInfo = toNumber(script.builtInFirstNightOrders.minionInfo);
  }
  if (script.builtInFirstNightEnabled.demonInfo) {
    meta.demonInfo = toNumber(script.builtInFirstNightOrders.demonInfo);
  }
  return meta;
}

function exportFabled(role: FabledDraft): ExportFabled {
  const name = cleanText(role.name);
  return {
    id: name,
    name,
    edition: "custom",
    team: "fabled",
    ability: cleanText(role.ability),
    image: cleanText(role.image),
    setup: setupValue(role.setup),
  };
}

function exportRole(role: RoleDraft, team: TeamKey): ExportCharacter {
  const name = cleanText(role.name);
  return {
    id: name,
    name,
    team,
    ability: cleanText(role.ability),
    image: cleanText(role.image),
    firstNight: toNumber(role.firstNight),
    firstNightReminder: cleanText(role.firstNightReminder),
    otherNight: toNumber(role.otherNight),
    otherNightReminder: cleanText(role.otherNightReminder),
    reminders: splitTags(role.reminders),
    remindersGlobal: splitTags(role.remindersGlobal),
    setup: setupValue(role.setup),
    flavor: cleanText(role.flavor),
  };
}

function exportJinx(jinx: JinxDraft, playCharacters: ExportPlayCharacter[]): ExportJinx {
  const name = cleanText(jinx.name);
  return {
    id: name,
    team: "jinx",
    name,
    ability: cleanText(jinx.ability),
    image: firstTargetImage(jinx, playCharacters),
  };
}

interface ExportPlayCharacter {
  name: string;
  image: string;
}

function collectExportPlayCharacters(script: ScriptDraft): ExportPlayCharacter[] {
  const characters: ExportPlayCharacter[] = [];
  const seenNames = new Set<string>();
  const addCharacter = (name: string | undefined, image: string | undefined) => {
    const cleanName = cleanText(name);
    if (!cleanName || seenNames.has(cleanName)) {
      return;
    }
    seenNames.add(cleanName);
    characters.push({
      name: cleanName,
      image: cleanText(image),
    });
  };

  script.fabled.forEach((role) => addCharacter(role.name, role.image));
  for (const team of exportTeamOrder) {
    script.teams[team].roles.filter((role) => role.selected).forEach((role) => addCharacter(role.name, role.image));
  }
  return characters;
}

function firstTargetImage(jinx: JinxDraft, playCharacters: ExportPlayCharacter[]) {
  const firstTarget = cleanText(jinx.targets[0]);
  const character = playCharacters.find((item) => item.name === firstTarget);
  return character?.image || cleanText(jinx.image);
}

function splitTags(values?: string[]) {
  return (values ?? [])
    .flatMap((value) => cleanText(value).split("||"))
    .map(cleanText)
    .filter(Boolean);
}

function setupValue(value?: 0 | 1) {
  return value === 1 ? 1 : 0;
}

function toNumber(value: unknown) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function cleanText(value: unknown) {
  return String(value ?? "").trim();
}
