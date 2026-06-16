import type { TextColorOption, ScriptColorKey, FormatState } from "./previewTypes";

export const SVG_WIDTH = 1100;
export const MIN_PREVIEW_HEIGHT = 1380;
export const PAGE_X = 54;
export const PAGE_Y = 38;
export const PAGE_WIDTH = 992;
export const CONTENT_X = 140;
export const CONTENT_WIDTH = 820;
export const CONTENT_RIGHT = CONTENT_X + CONTENT_WIDTH;
export const CONTENT_CENTER = CONTENT_X + CONTENT_WIDTH / 2;
export const HEADER_TITLE_Y = 112;
export const HEADER_AUTHOR_Y = 164;
export const FIRST_SECTION_WITH_AUTHOR_Y = 180;
export const FIRST_SECTION_WITHOUT_AUTHOR_Y = 146;
export const COLUMN_GAP = 32;
export const COLUMN_WIDTH = (CONTENT_WIDTH - COLUMN_GAP) / 2;
export const SINGLE_COLUMN_WIDTH_RATIO = 0.7;
export const SINGLE_COLUMN_WIDTH = CONTENT_WIDTH * SINGLE_COLUMN_WIDTH_RATIO;
export const ROLE_TEXT_WIDTH_PADDING = 8;
export const ROLE_ICON_SIZE = 54;
export const ROLE_ICON_GAP = 12;

// Script font size tuning.
export const SCRIPT_TITLE_FONT_SIZE = 56;
export const SCRIPT_AUTHOR_FONT_SIZE = 22;
export const SECTION_HEADING_FONT_SIZE = 25;
export const ROLE_NAME_FONT_SIZE = 22;
export const ROLE_ABILITY_FONT_SIZE = 16;
export const ROLE_FALLBACK_FONT_SIZE = 24;
export const NIGHT_LABEL_FONT_SIZE = 22;
export const NIGHT_FALLBACK_FONT_SIZE = 18;

export const ROLE_NAME_LINE_HEIGHT = 29;
export const ROLE_ABILITY_LINE_HEIGHT = 20;
export const ROLE_NAME_TO_ABILITY_GAP = 0;
export const SECTION_HEADING_LINE_GAP = 16;
export const SECTION_BOTTOM_GAP = 10;
export const ROW_GAP = 8;

// Jinx text blocks rendered below the first affected character.
export const JINX_RULE_FONT_SIZE = 13;
export const JINX_RULE_LINE_HEIGHT = 17;
export const JINX_RULE_TOP_GAP = 7;
export const JINX_RULE_BOX_GAP = 5;
export const JINX_RULE_PADDING_X = 8;
export const JINX_RULE_PADDING_Y = 6;
export const JINX_RULE_BOX_RADIUS = 5;
export const JINX_RULE_BOX_FILL = "#eceff3";
export const JINX_RULE_BOX_STROKE = "#d7dbe2";
export const JINX_RULE_TEXT_COLOR = "#38404a";

// Night order rail tuning.
export const RAIL_WIDTH = 54;
export const LEFT_RAIL_X = 54;
export const RIGHT_RAIL_X = PAGE_X + PAGE_WIDTH - RAIL_WIDTH;
export const NIGHT_RAIL_VERTICAL_MARGIN = 42;
export const NIGHT_LABEL_FIRST_Y = 22;
export const NIGHT_LABEL_SECOND_Y = 52;
export const NIGHT_LABEL_TO_ICON_GAP = 14;
export const NIGHT_ICON_SIZE = 37;
export const NIGHT_ICON_GAP = 6;
export const NIGHT_LABEL_X = RAIL_WIDTH / 2;
export const NIGHT_ICON_X = (RAIL_WIDTH - NIGHT_ICON_SIZE) / 2;
export const NIGHT_ICON_CENTER = NIGHT_ICON_SIZE / 2;
export const NIGHT_ICON_FALLBACK_RADIUS = NIGHT_ICON_SIZE / 2 - 1;
export const NIGHT_ICON_START_Y = NIGHT_LABEL_SECOND_Y + NIGHT_LABEL_TO_ICON_GAP;
export const NIGHT_ICON_STEP = NIGHT_ICON_SIZE + NIGHT_ICON_GAP;
export const MIN_CHARACTER_HIGHLIGHT_NAME_LENGTH = 2;

export const PREVIEW_BASE_WIDTH = 930;
export const PREVIEW_CANVAS_TOP_PADDING = 22;
export const PREVIEW_CANVAS_BOTTOM_SAFE_SPACE = 220;
export const PREVIEW_MIN_ZOOM = 0.45;
export const PREVIEW_MAX_ZOOM = 3;
export const PREVIEW_WHEEL_ZOOM_SPEED = 0.0015;
export const PREVIEW_ZOOM_SMOOTHING = 0.22;
export const PREVIEW_ZOOM_SETTLE_EPSILON = 0.001;
export const PREVIEW_PAN_SETTLE_EPSILON = 0.25;

export const teamColors: Record<ScriptColorKey, string> = {
  townsfolk: "rgb(14, 127, 207)",
  outsider: "rgb(57, 136, 169)",
  minion: "rgb(143, 23, 1)",
  demon: "rgb(83, 43, 43)",
  traveler: "rgb(103, 14, 171)",
  fabled: "rgb(255, 166, 72)",
};

export const DEFAULT_TEXT_COLOR = "rgb(20, 26, 34)";
export const SCRIPT_PAGE_BACKGROUND = "rgb(255, 253, 248)";
export const TRANSPARENT_COLOR = "rgba(0, 0, 0, 0)";

export const emptyFormatState: FormatState = {
  bold: false,
  italic: false,
  underline: false,
  textColor: null,
  backgroundColor: null,
};

export const textColorOptions: TextColorOption[] = [
  { label: "默认", color: DEFAULT_TEXT_COLOR, clear: true },
  { label: "镇民", color: teamColors.townsfolk },
  { label: "外来", color: teamColors.outsider },
  { label: "爪牙", color: teamColors.minion },
  { label: "恶魔", color: teamColors.demon },
  { label: "旅行", color: teamColors.traveler },
];

export const backgroundColorOptions: TextColorOption[] = [
  { label: "黄", color: "rgb(255, 241, 168)" },
  { label: "蓝", color: "rgb(223, 242, 255)" },
  { label: "红", color: "rgb(255, 225, 220)" },
  { label: "紫", color: "rgb(237, 220, 255)" },
  { label: "无", color: "transparent", clear: true },
];
