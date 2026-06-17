import { computed, onMounted, reactive, ref } from "vue";
import { sampleScript, teamOrder } from "../data/sampleScript";
import type { FabledDraft, JinxDraft, PlayCharacterSummary, RoleDraft, TeamKey } from "../types";
import {
  jinxRecordToDraft,
  loadMatchingJinxRecords,
} from "../utils/jinxLibrary";
import { isBatchExportMode } from "../utils/batchExportClient";
import { loadPlayFromJson } from "../utils/playJson";

export function useScriptEditor() {
  const script = reactive(structuredClone(sampleScript));
  const selectedTeam = ref<TeamKey>("townsfolk");
  const importError = ref("");
  const removedAutoJinxNames = new Set<string>();
  const jinxIncludedPreferenceByName = new Map<string, boolean>();

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
    script.fabled.push({
      id: crypto.randomUUID(),
      name: "新传奇角色",
      ability: "",
      ...role,
    });
    void addMatchingDatabaseJinxes();
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
    rememberJinxIncluded(nextJinx);
    script.jinxes.push(nextJinx);
  }

  function removeJinx(id: string) {
    const removed = script.jinxes.find((jinx) => jinx.id === id);
    if (removed) {
      removedAutoJinxNames.add(normalizeJinxName(removed.name));
    }
    script.jinxes = script.jinxes.filter((jinx) => jinx.id !== id);
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
    };
    if (previousName !== script.jinxes[index].name) {
      clearJinxSuppression(previousName);
    }
    clearJinxSuppression(script.jinxes[index].name);
    rememberJinxIncluded(script.jinxes[index]);
  }

  function setJinxIncluded(id: string, included: boolean) {
    const jinx = script.jinxes.find((item) => item.id === id);
    if (!jinx) {
      return;
    }
    jinx.included = included;
    rememberJinxIncluded(jinx);
  }

  function addRole(team: TeamKey, role?: RoleDraft) {
    script.teams[team].roles.push({
      id: crypto.randomUUID(),
      name: "新角色",
      ability: "",
      selected: true,
      setup: 0,
      firstNight: 0,
      otherNight: 0,
      ...role,
    });
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

  async function loadPlayText(rawText: string, fileName: string) {
    const parsed = JSON.parse(rawText);
    const loaded = loadPlayFromJson(parsed, fileName);
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
    resetJinxMemory();
    for (const team of Object.values(script.teams)) {
      team.roles = [];
    }
    importError.value = "";
  }

  async function addMatchingDatabaseJinxes(options: { includeNew?: boolean } = {}) {
    const includeNew = options.includeNew ?? true;
    const characters = collectPlayCharacters();
    const names = characters.map((character) => character.name);
    const records = await loadMatchingJinxRecords(names);
    const existingByName = new Map(script.jinxes.map((jinx) => [normalizeJinxName(jinx.name), jinx]));
    for (const record of records) {
      const normalizedName = normalizeJinxName(record.name);
      if (removedAutoJinxNames.has(normalizedName)) {
        continue;
      }
      const draft = jinxRecordToDraft(record);
      draft.included = jinxIncludedPreferenceByName.get(normalizedName) ?? includeNew;
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
        if (existing.included === undefined) {
          existing.included = jinxIncludedPreferenceByName.get(normalizedName) ?? includeNew;
        }
        rememberJinxIncluded(existing);
        continue;
      }
      script.jinxes.push(draft);
      rememberJinxIncluded(draft);
      existingByName.set(normalizedName, draft);
    }
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
      if (jinx.targets.some((target) => !availableNames.has(target))) {
        jinx.included = false;
        rememberJinxIncluded(jinx);
      }
    }
  }

  function rememberJinxIncluded(jinx: JinxDraft) {
    const normalizedName = normalizeJinxName(jinx.name);
    if (normalizedName) {
      jinxIncludedPreferenceByName.set(normalizedName, jinx.included !== false);
    }
  }

  function clearJinxSuppression(name: string) {
    const normalizedName = normalizeJinxName(name);
    if (normalizedName) {
      removedAutoJinxNames.delete(normalizedName);
    }
  }

  function resetJinxMemory() {
    removedAutoJinxNames.clear();
    jinxIncludedPreferenceByName.clear();
  }

  function normalizeJinxName(name: string) {
    return name
      .split(/[&＆]/u)
      .map((item) => item.trim())
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
    removeFabled,
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
