import { computed, onMounted, reactive, ref } from "vue";
import { sampleScript, teamOrder } from "../data/sampleScript";
import type { RoleDraft, TeamKey } from "../types";
import { loadPlayFromJson } from "../utils/playJson";

export function useScriptEditor() {
  const script = reactive(structuredClone(sampleScript));
  const selectedTeam = ref<TeamKey>("townsfolk");
  const importError = ref("");

  const activeTeam = computed(() => script.teams[selectedTeam.value] ?? script.teams.townsfolk);
  const selectedRoleCount = computed(() =>
    Object.values(script.teams).reduce(
      (total, team) => total + team.roles.filter((role) => role.selected).length,
      0,
    ),
  );
  onMounted(() => {
    loadSamplePlay();
  });

  function addFabled() {
    script.fabled.push({
      id: crypto.randomUUID(),
      name: "新传奇角色",
      ability: "",
    });
  }

  function removeFabled(id: string) {
    script.fabled = script.fabled.filter((role) => role.id !== id);
  }

  function addJinx() {
    script.jinxes.push({
      id: crypto.randomUUID(),
      name: "新相克规则",
      ability: "",
      targets: [],
    });
  }

  function removeJinx(id: string) {
    script.jinxes = script.jinxes.filter((jinx) => jinx.id !== id);
  }

  function addRole(team: TeamKey) {
    script.teams[team].roles.push({
      id: crypto.randomUUID(),
      name: "新角色",
      ability: "",
      selected: true,
      setup: 0,
      firstNight: 0,
      otherNight: 0,
    });
  }

  function removeRole(team: TeamKey, id: string) {
    script.teams[team].roles = script.teams[team].roles.filter((role) => role.id !== id);
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
    Object.assign(script, loaded.script);
    importError.value = "";
  }

  return {
    script,
    selectedTeam,
    importError,
    teamOrder,
    activeTeam,
    selectedRoleCount,
    addFabled,
    removeFabled,
    addJinx,
    removeJinx,
    addRole,
    removeRole,
    roleStateLabel,
    handleJsonUpload,
  };
}
