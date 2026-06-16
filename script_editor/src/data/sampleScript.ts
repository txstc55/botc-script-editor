import type { ScriptDraft, TeamKey } from "../types";
import {
  createDefaultBuiltInFirstNightEnabled,
  createDefaultBuiltInFirstNightOrders,
} from "../utils/nightOrders";

export const teamOrder: TeamKey[] = [
  "townsfolk",
  "outsider",
  "minion",
  "demon",
  "traveler",
];

export const sampleScript: ScriptDraft = {
  name: "Custom Clocktower Script",
  author: "Script Author",
  builtInFirstNightOrders: createDefaultBuiltInFirstNightOrders(),
  builtInFirstNightEnabled: createDefaultBuiltInFirstNightEnabled(),
  fabled: [
    {
      id: "djinn",
      name: "Djinn",
      ability: "Use the jinx rules. All players know what they are.",
    },
  ],
  jinxes: [
    {
      id: "cannibal-poppy-grower",
      name: "Cannibal & Poppy Grower",
      ability:
        "If the Cannibal gains the Poppy Grower ability, Minions and Demons learn each other when the Cannibal dies or loses the Poppy Grower ability.",
      included: true,
      targets: ["Cannibal", "Poppy Grower"],
    },
  ],
  teams: {
    townsfolk: {
      key: "townsfolk",
      label: "镇民",
      roles: [
        {
          id: "washerwoman",
          name: "Washerwoman",
          selected: true,
          setup: 0,
          ability:
            "You start knowing that 1 of 2 players is a particular Townsfolk.",
        },
        {
          id: "undertaker",
          name: "Undertaker",
          selected: true,
          setup: 0,
          ability:
            "Each night*, you learn which character died by execution today.",
        },
      ],
    },
    outsider: {
      key: "outsider",
      label: "外来者",
      roles: [
        {
          id: "drunk",
          name: "Drunk",
          selected: true,
          setup: 1,
          ability:
            "You do not know you are the Drunk. You think you are a Townsfolk character, but you are not.",
        },
      ],
    },
    minion: {
      key: "minion",
      label: "爪牙",
      roles: [
        {
          id: "poisoner",
          name: "Poisoner",
          selected: true,
          setup: 0,
          ability:
            "Each night, choose a player: they are poisoned tonight and tomorrow day.",
        },
      ],
    },
    demon: {
      key: "demon",
      label: "恶魔",
      roles: [
        {
          id: "imp",
          name: "Imp",
          selected: true,
          setup: 0,
          ability:
            "Each night*, choose a player: they die. If you kill yourself this way, a Minion becomes the Imp.",
        },
      ],
    },
    traveler: {
      key: "traveler",
      label: "旅行者",
      roles: [
        {
          id: "gunslinger",
          name: "Gunslinger",
          selected: false,
          setup: 0,
          ability:
            "Each day, after the first vote has been tallied, you may choose a player that voted: they die.",
        },
      ],
    },
  },
};
