export type TeamKey =
  | "townsfolk"
  | "outsider"
  | "minion"
  | "demon"
  | "traveler";

export type BuiltInFirstNightOrderKey = "minionInfo" | "demonInfo";
export type BuiltInFirstNightOrders = Record<BuiltInFirstNightOrderKey, number>;
export type BuiltInFirstNightEnabled = Record<BuiltInFirstNightOrderKey, boolean>;

export interface RoleDraft {
  id: string;
  name: string;
  ability: string;
  abilityHtml?: string;
  selected: boolean;
  setup?: 0 | 1;
  image?: string;
  firstNight?: number;
  firstNightReminder?: string;
  otherNight?: number;
  otherNightReminder?: string;
  reminders?: string[];
  remindersGlobal?: string[];
  flavor?: string;
}

export interface FabledDraft {
  id: string;
  name: string;
  ability: string;
  abilityHtml?: string;
  image?: string;
  firstNight?: number;
  firstNightReminder?: string;
  otherNight?: number;
  otherNightReminder?: string;
  reminders?: string[];
  remindersGlobal?: string[];
  setup?: 0 | 1;
  flavor?: string;
}

export interface JinxDraft {
  id: string;
  name: string;
  ability: string;
  image?: string;
  included?: boolean;
  targets: string[];
}

export interface PlayCharacterSummary {
  id: string;
  name: string;
  image?: string;
}

export interface TeamConfig {
  key: TeamKey;
  label: string;
  roles: RoleDraft[];
}

export interface ScriptDraft {
  name: string;
  author: string;
  builtInFirstNightOrders: BuiltInFirstNightOrders;
  builtInFirstNightEnabled: BuiltInFirstNightEnabled;
  fabled: FabledDraft[];
  jinxes: JinxDraft[];
  teams: Record<TeamKey, TeamConfig>;
}

export interface PlayCleanupReport {
  fileName: string;
  roleCount: number;
  fabledCount: number;
  jinxCount: number;
  skippedCount: number;
  normalizedTeamCount: number;
  normalizedJinxTeamCount: number;
  normalizedSetupCount: number;
  backfilledReminderCount: number;
}
