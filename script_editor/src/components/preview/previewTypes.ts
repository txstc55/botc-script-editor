import type { FabledDraft, RoleDraft, TeamKey } from "../../types";

export type ScriptColorKey = TeamKey | "fabled";
export type PreviewSectionKey = ScriptColorKey;
export type PreviewRole = RoleDraft | FabledDraft;

export interface PreviewSection {
  key: PreviewSectionKey;
  label: string;
  roles: PreviewRole[];
}

export interface NightOrderItem {
  id: string;
  name: string;
  image?: string;
  order: number;
  team: TeamKey;
  color: string;
}

export interface SvgRoleLayout {
  id: string;
  role: PreviewRole;
  team: PreviewSectionKey;
  color: string;
  x: number;
  y: number;
  textX: number;
  imageX: number;
  imageY: number;
  imageCenterX: number;
  imageCenterY: number;
  fallbackLetter: string;
  nameLines: string[];
  abilityLines: string[];
  nameStartY: number;
  abilityX: number;
  abilityY: number;
  abilityWidth: number;
  abilityHeight: number;
  height: number;
}

export interface SvgSectionLayout {
  key: PreviewSectionKey;
  heading: string;
  color: string;
  y: number;
  headingY: number;
  lineX: number;
  lineY: number;
  roles: SvgRoleLayout[];
  height: number;
}

export interface SvgPreviewLayout {
  height: number;
  pageHeight: number;
  nightRailContentY: number;
  sections: SvgSectionLayout[];
  firstNightItems: NightOrderItem[];
  otherNightItems: NightOrderItem[];
}

export interface TextColorOption {
  label: string;
  color: string;
  clear?: boolean;
}

export interface FormatState {
  bold: boolean;
  italic: boolean;
  underline: boolean;
  textColor: string | null;
  backgroundColor: string | null;
}

export interface AbilityHighlightRule {
  text: string;
  color: string;
  priority: number;
}

export interface PreviewPanGesture {
  pointerId: number;
  startX: number;
  startY: number;
  startPanX: number;
  startPanY: number;
}
