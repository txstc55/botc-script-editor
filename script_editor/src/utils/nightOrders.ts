import type {
  BuiltInFirstNightEnabled,
  BuiltInFirstNightOrderKey,
  BuiltInFirstNightOrders,
  RoleDraft,
  ScriptDraft,
  TeamKey,
} from "../types";

export interface NightOrderBaseItem {
  id: string;
  name: string;
  image?: string;
  reminder?: string;
  order: number;
  team: TeamKey;
  builtIn?: boolean;
}

export interface BuiltInFirstNightOrderDefinition {
  id: BuiltInFirstNightOrderKey;
  name: string;
  defaultOrder: number;
  reminder: string;
  image: string;
  team: TeamKey;
}

export const builtInFirstNightOrderDefinitions: BuiltInFirstNightOrderDefinition[] = [
  {
    id: "minionInfo",
    name: "爪牙信息",
    defaultOrder: 4.5,
    reminder: "如果有七名或更多玩家，唤醒所有爪牙：展示“他是恶魔”信息标记。指向恶魔。",
    image: "https://clocktower-wiki.gstonegames.com/images/thumb/8/85/Mi.png/180px-Mi.png",
    team: "minion",
  },
  {
    id: "demonInfo",
    name: "恶魔信息",
    defaultOrder: 7.5,
    reminder:
      "如果有七名或更多玩家，唤醒恶魔：展示“他们是你的爪牙”信息标记。指向所有爪牙。 展示“这些角色不在场”信息标记。展示三个不在场的善良角色。",
    image: "https://clocktower-wiki.gstonegames.com/images/thumb/1/18/Di.png/180px-Di.png",
    team: "demon",
  },
];

export function createDefaultBuiltInFirstNightOrders(): BuiltInFirstNightOrders {
  return Object.fromEntries(
    builtInFirstNightOrderDefinitions.map((definition) => [definition.id, definition.defaultOrder]),
  ) as BuiltInFirstNightOrders;
}

export function createDefaultBuiltInFirstNightEnabled(): BuiltInFirstNightEnabled {
  return Object.fromEntries(
    builtInFirstNightOrderDefinitions.map((definition) => [definition.id, true]),
  ) as BuiltInFirstNightEnabled;
}

export function buildFirstNightOrderItems(script: ScriptDraft): NightOrderBaseItem[] {
  return sortNightOrderItems([
    ...builtInFirstNightOrderDefinitions
      .filter((definition) => script.builtInFirstNightEnabled?.[definition.id] ?? true)
      .map((definition) => ({
        id: `builtin-first-night-${definition.id}`,
        name: definition.name,
        image: definition.image,
        reminder: definition.reminder,
        order: script.builtInFirstNightOrders[definition.id] ?? definition.defaultOrder,
        team: definition.team,
        builtIn: true,
      })),
    ...buildRoleNightOrderItems(script, "firstNight"),
  ]);
}

export function buildOtherNightOrderItems(script: ScriptDraft): NightOrderBaseItem[] {
  return buildRoleNightOrderItems(script, "otherNight");
}

export function formatNightOrder(order: number) {
  if (Number.isInteger(order)) {
    return String(order);
  }
  return order.toFixed(2);
}

function buildRoleNightOrderItems(
  script: ScriptDraft,
  field: "firstNight" | "otherNight",
): NightOrderBaseItem[] {
  return sortNightOrderItems(
    Object.values(script.teams)
      .filter((team) => team.key !== "traveler")
      .flatMap((team) =>
        team.roles
          .filter((role) => role.selected)
          .map((role) => roleNightOrderItem(role, team.key, field)),
      )
      .filter((item) => item.order > 0),
  );
}

function roleNightOrderItem(
  role: RoleDraft,
  team: TeamKey,
  field: "firstNight" | "otherNight",
): NightOrderBaseItem {
  return {
    id: `${field}-${role.id}`,
    name: role.name,
    image: role.image,
    reminder: field === "firstNight" ? role.firstNightReminder : role.otherNightReminder,
    order: role[field] ?? 0,
    team,
  };
}

function sortNightOrderItems(items: NightOrderBaseItem[]) {
  return [...items].sort((left, right) =>
    left.order - right.order || left.name.localeCompare(right.name, "zh-Hans-CN"),
  );
}
