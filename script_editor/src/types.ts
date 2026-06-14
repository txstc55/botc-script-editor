export type TeamKey =
  | "townsfolk"
  | "outsider"
  | "minion"
  | "demon"
  | "traveler";

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
}

export interface FabledDraft {
  id: string;
  name: string;
  ability: string;
  abilityHtml?: string;
  image?: string;
}

export interface JinxDraft {
  id: string;
  name: string;
  ability: string;
  targets: string[];
}

export interface TeamConfig {
  key: TeamKey;
  label: string;
  roles: RoleDraft[];
}

export interface ScriptDraft {
  name: string;
  author: string;
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
