import { computed, onMounted, reactive, ref } from "vue";
import { sampleScript, teamOrder } from "../data/sampleScript";
import type { FabledDraft, JinxDraft, PlayCharacterSummary, RoleDraft, TeamKey } from "../types";
import {
  jinxHasUnavailableTargets,
  jinxRecordToDraft,
  loadMatchingJinxRecords,
} from "../utils/jinxLibrary";
import { isBatchExportMode } from "../utils/batchExportClient";
import { loadPlayFromJson } from "../utils/playJson";
import { hydratePlayRoleIds } from "../utils/roleIdLibrary";

export function useScriptEditor() {
  const script = reactive(structuredClone(sampleScript));
  const selectedTeam = ref<TeamKey>("townsfolk");
  const importError = ref("");
  const disabledJinxNames = new Set<string>();
  const removedJinxNames = new Set<string>();
  let jinxMatchRevision = 0;

  const activeTeam = computed(() => script.teams[selectedTeam.value] ?? script.teams.townsfolk);
  const selectedRoleCount = computed(() =>
    Object.values(script.teams).reduce(
      (total, team) => total + team.roles.filter((role) => role.selected).length,
      0,
    ),
  );
  const playCharacters = computed(() => collectPlayCharacters());

  onMounted(() => {
    if (!isBatchExportMode()) {
      loadSamplePlay();
    }
  });

  function addFabled(role?: FabledDraft) {
    const nextRole: FabledDraft = {
      id: crypto.randomUUID(),
      name: "新传奇角色",
      ability: "",
      ...role,
    };
    script.fabled.push(nextRole);
    markJinxTargetAvailable(nextRole.name);
    void addMatchingDatabaseJinxes();
  }

  function addNote() {
    script.notes.push({
      id: crypto.randomUUID(),
      text: "新说明",
    });
  }

  function removeNote(id: string) {
    script.notes = script.notes.filter((note) => note.id !== id);
  }

  function removeFabled(id: string) {
    const removedRole = script.fabled.find((role) => role.id === id);
    script.fabled = script.fabled.filter((role) => role.id !== id);
    if (removedRole) {
      removeJinxesRelatedToCharacter(removedRole.name);
    }
  }

  function updateFabled(id: string, nextRole: FabledDraft) {
    const index = script.fabled.findIndex((role) => role.id === id);
    if (index < 0) {
      return;
    }
    const previousName = script.fabled[index].name;
    script.fabled[index] = {
      ...script.fabled[index],
      ...nextRole,
      id,
    };
    if (previousName !== script.fabled[index].name) {
      removeJinxesRelatedToCharacter(previousName);
    }
    markJinxTargetAvailable(script.fabled[index].name);
    void addMatchingDatabaseJinxes();
  }

  function addJinx(jinx?: JinxDraft) {
    const nextJinx = {
      id: crypto.randomUUID(),
      name: "新相克规则",
      ability: "",
      image: "",
      included: true,
      targets: [],
      ...jinx,
    };
    clearJinxSuppression(nextJinx.name);
    rememberJinxIncluded(nextJinx, true);
    script.jinxes.push(nextJinx);
  }

  function removeJinx(id: string) {
    const removed = script.jinxes.find((jinx) => jinx.id === id);
    if (!removed) {
      return;
    }
    const normalizedName = normalizeJinxName(removed.name);
    rememberJinxRemoved(removed.name);
    script.jinxes = script.jinxes.filter((jinx) => normalizeJinxName(jinx.name) !== normalizedName);
  }

  function updateJinx(id: string, nextJinx: JinxDraft) {
    const index = script.jinxes.findIndex((jinx) => jinx.id === id);
    if (index < 0) {
      return;
    }
    const previousName = script.jinxes[index].name;
    script.jinxes[index] = {
      ...script.jinxes[index],
      ...nextJinx,
      id,
      initiallyMissingTargets: undefined,
    };
    if (previousName !== script.jinxes[index].name) {
      clearJinxSuppression(previousName);
    }
    clearJinxSuppression(script.jinxes[index].name);
    rememberJinxIncluded(script.jinxes[index], true);
  }

  function setJinxIncluded(id: string, included: boolean) {
    const jinx = script.jinxes.find((item) => item.id === id);
    if (!jinx) {
      return;
    }
    jinx.included = included;
    rememberJinxIncluded(jinx, true);
  }

  function addRole(team: TeamKey, role?: RoleDraft) {
    const nextRole: RoleDraft = {
      id: crypto.randomUUID(),
      name: "新角色",
      ability: "",
      selected: true,
      setup: 0,
      firstNight: 0,
      otherNight: 0,
      ...role,
    };
    script.teams[team].roles.push(nextRole);
    markJinxTargetAvailable(nextRole.name);
    void addMatchingDatabaseJinxes();
  }

  function removeRole(team: TeamKey, id: string) {
    const removedRole = script.teams[team].roles.find((role) => role.id === id);
    script.teams[team].roles = script.teams[team].roles.filter((role) => role.id !== id);
    if (removedRole) {
      removeJinxesRelatedToCharacter(removedRole.name);
    }
  }

  function updateRole(team: TeamKey, id: string, nextRole: RoleDraft) {
    const index = script.teams[team].roles.findIndex((role) => role.id === id);
    if (index < 0) {
      return;
    }
    const previousName = script.teams[team].roles[index].name;
    script.teams[team].roles[index] = {
      ...script.teams[team].roles[index],
      ...nextRole,
      id,
      selected: script.teams[team].roles[index].selected,
    };
    if (previousName !== script.teams[team].roles[index].name) {
      removeJinxesRelatedToCharacter(previousName);
    }
    markJinxTargetAvailable(script.teams[team].roles[index].name);
    void addMatchingDatabaseJinxes();
  }

  function setRoleSelected(team: TeamKey, id: string, selected: boolean) {
    const role = script.teams[team].roles.find((item) => item.id === id);
    if (!role || role.selected === selected) {
      return;
    }
    role.selected = selected;
    if (selected) {
      void addMatchingDatabaseJinxes();
    } else {
      disableJinxesWithUnavailableTargets();
    }
  }

  function roleStateLabel(role: RoleDraft) {
    return role.selected ? "已加入" : "候选";
  }

  async function handleJsonUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    try {
      await loadPlayText(await file.text(), file.name);
      input.value = "";
    } catch (error) {
      importError.value = error instanceof Error ? error.message : "无法读取这个 JSON";
    }
  }

  async function loadSamplePlay() {
    try {
      const response = await fetch("/samples/瓦釜雷鸣.json");
      if (!response.ok) {
        return;
      }
      await loadPlayText(await response.text(), "瓦釜雷鸣.json");
    } catch {
      // 示例文件不存在时保持内置草稿。
    }
  }

  async function loadPlayText(rawText: string, fileName: string, runtimeNotes: string[] = []) {
    const parsed = await hydratePlayRoleIds(JSON.parse(rawText));
    const loaded = loadPlayFromJson(parsed, fileName);
    if (runtimeNotes.length) {
      loaded.script.notes = runtimeNotes.map((text, index) => ({
        id: `runtime-note-${index}`,
        text,
      }));
    }
    resetJinxMemory();
    Object.assign(script, loaded.script);
    importError.value = "";
    disableJinxesWithUnavailableTargets();
    await addMatchingDatabaseJinxes({ includeNew: false });
    disableJinxesWithUnavailableTargets();
  }

  function clearScript() {
    script.name = "";
    script.author = "";
    script.fabled = [];
    script.jinxes = [];
    script.notes = [];
    resetJinxMemory();
    for (const team of Object.values(script.teams)) {
      team.roles = [];
    }
    importError.value = "";
  }

  async function addMatchingDatabaseJinxes(options: { includeNew?: boolean } = {}) {
    rememberCurrentJinxStates();
    const revision = ++jinxMatchRevision;
    const includeNew = options.includeNew ?? false;
    const characters = collectPlayCharacters();
    const names = characters.map((character) => character.name);
    const records = await loadMatchingJinxRecords(names);
    if (revision !== jinxMatchRevision) {
      return;
    }

    const existingByName = new Map(script.jinxes.map((jinx) => [normalizeJinxName(jinx.name), jinx]));
    for (const record of records) {
      const normalizedName = normalizeJinxName(record.name);
      if (removedJinxNames.has(normalizedName)) {
        continue;
      }
      const draft = jinxRecordToDraft(record);
      draft.included = includeNew && !disabledJinxNames.has(normalizedName);
      draft.image = imageForJinxTargets(draft.targets, characters) || draft.image;
      const existing = existingByName.get(normalizedName);
      if (existing) {
        if (!existing.ability.trim() && draft.ability.trim()) {
          existing.ability = draft.ability;
        }
        if (!existing.targets.length && draft.targets.length) {
          existing.targets = draft.targets;
        }
        if (!existing.image && draft.image) {
          existing.image = draft.image;
        }
        if (disabledJinxNames.has(normalizedName)) {
          existing.included = false;
        } else if (existing.included === undefined) {
          existing.included = includeNew;
        }
        continue;
      }
      script.jinxes.push(draft);
      existingByName.set(normalizedName, draft);
    }
    applyJinxSuppressions();
  }

  function collectPlayCharacters(): PlayCharacterSummary[] {
    const result: PlayCharacterSummary[] = [];
    const seenNames = new Set<string>();
    const addCharacter = (character: PlayCharacterSummary) => {
      const name = character.name.trim();
      if (!name || seenNames.has(name)) {
        return;
      }
      seenNames.add(name);
      result.push({
        ...character,
        name,
      });
    };

    for (const role of script.fabled) {
      addCharacter({ id: role.id, name: role.name, image: role.image });
    }
    for (const team of Object.values(script.teams)) {
      for (const role of team.roles) {
        if (role.selected) {
          addCharacter({ id: role.id, name: role.name, image: role.image });
        }
      }
    }
    return result;
  }

  function imageForJinxTargets(targets: string[], characters: PlayCharacterSummary[]) {
    const targetNames = targets.length ? targets : [];
    const target = targetNames
      .map((name) => characters.find((character) => character.name === name))
      .find((character) => character?.image);
    return target?.image ?? "";
  }

  function removeJinxesRelatedToCharacter(name: string) {
    const targetName = name.trim();
    if (!targetName) {
      return;
    }
    for (const jinx of script.jinxes) {
      if (jinx.targets.some((target) => target.trim() === targetName)) {
        rememberJinxIncluded(jinx);
      }
    }
    script.jinxes = script.jinxes.filter((jinx) => !jinx.targets.some((target) => target.trim() === targetName));
  }

  function disableJinxesWithUnavailableTargets() {
    const availableNames = new Set(collectPlayCharacters().map((character) => character.name));
    for (const jinx of script.jinxes) {
      if (jinxHasUnavailableTargets(jinx, availableNames)) {
        jinx.included = false;
        rememberJinxIncluded(jinx);
      }
    }
  }

  function markJinxTargetAvailable(name: string) {
    const targetName = name.trim();
    if (!targetName) {
      return;
    }
    for (const jinx of script.jinxes) {
      if (!jinx.initiallyMissingTargets?.includes(targetName)) {
        continue;
      }
      const remaining = jinx.initiallyMissingTargets.filter((target) => target !== targetName);
      jinx.initiallyMissingTargets = remaining.length ? remaining : undefined;
    }
  }

  function rememberJinxIncluded(jinx: JinxDraft, explicit = false) {
    const normalizedName = normalizeJinxName(jinx.name);
    if (!normalizedName) {
      return;
    }
    if (jinx.included === false) {
      disabledJinxNames.add(normalizedName);
    } else if (explicit) {
      disabledJinxNames.delete(normalizedName);
    }
  }

  function rememberCurrentJinxStates() {
    for (const jinx of script.jinxes) {
      rememberJinxIncluded(jinx);
    }
  }

  function rememberJinxRemoved(name: string) {
    const normalizedName = normalizeJinxName(name);
    if (normalizedName) {
      removedJinxNames.add(normalizedName);
      disabledJinxNames.delete(normalizedName);
    }
  }

  function clearJinxSuppression(name: string) {
    const normalizedName = normalizeJinxName(name);
    removedJinxNames.delete(normalizedName);
    disabledJinxNames.delete(normalizedName);
  }

  function applyJinxSuppressions() {
    script.jinxes = script.jinxes.filter((jinx) => !removedJinxNames.has(normalizeJinxName(jinx.name)));
    for (const jinx of script.jinxes) {
      if (disabledJinxNames.has(normalizeJinxName(jinx.name))) {
        jinx.included = false;
      }
    }
  }

  function resetJinxMemory() {
    jinxMatchRevision += 1;
    disabledJinxNames.clear();
    removedJinxNames.clear();
  }

  function normalizeJinxName(name: string) {
    return name
      .normalize("NFKC")
      .split("&")
      .map((item) => item.trim().replace(/\s+/gu, " "))
      .filter(Boolean)
      .join("&") || name.trim();
  }

  return {
    script,
    selectedTeam,
    importError,
    teamOrder,
    activeTeam,
    selectedRoleCount,
    playCharacters,
    addFabled,
    addNote,
    removeFabled,
    removeNote,
    updateFabled,
    addJinx,
    removeJinx,
    updateJinx,
    setJinxIncluded,
    addRole,
    removeRole,
    updateRole,
    setRoleSelected,
    roleStateLabel,
    handleJsonUpload,
    loadPlayText,
    clearScript,
  };
}
