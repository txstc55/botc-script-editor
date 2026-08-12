#!/usr/bin/env python3
"""Detect standard bottom-of-board explanations without changing script JSON."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


MINION_STYLE = "color: rgb(143, 23, 1); font-weight: 900;"
TRAVELER_STYLE = "color: rgb(103, 14, 171); font-weight: 900;"
TOWNSFOLK_STYLE = "color: rgb(14, 127, 207); font-weight: 900;"


@dataclass(frozen=True)
class NoteDefinition:
  key: str
  label: str
  text: str
  html: str
  matches: Callable[[str], bool]
  position_marker: str


NOTE_DEFINITIONS = (
  NoteDefinition(
    key="possible",
    label="可能",
    text="可能：某件事“可能”发生，代表说书人决定该事情是否发生。",
    html=(
      f'<span style="{TRAVELER_STYLE}">可能</span>：'
      "某件事“可能”发生，代表说书人决定该事情是否发生。"
    ),
    matches=lambda text: bool(re.search(r"某件事(?:情)?.{0,3}可能.{0,3}发生", text)),
    position_marker="某件事情",
  ),
  NoteDefinition(
    key="madness",
    label="疯狂",
    text=(
      "疯狂：当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力的证明某件事情，"
      "如不这么做会受到惩罚。"
    ),
    html=(
      f'<span style="{TRAVELER_STYLE}">疯狂</span>：'
      f'当你陷入“<span style="{TRAVELER_STYLE}">疯狂</span>”时，意味着你需要向其他玩家'
      f'<span style="{TOWNSFOLK_STYLE}">有诚意且努力</span>的证明某件事情，如不这么做会'
      f'<span style="{MINION_STYLE}">受到惩罚</span>。'
    ),
    matches=lambda text: "当你陷入" in text and "疯狂" in text and "受到惩罚" in text,
    position_marker="当你陷入",
  ),
  NoteDefinition(
    key="poison_drunk",
    label="中毒/醉酒",
    text=(
      "中毒/醉酒：中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
      "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。"
      "醉酒同理。"
    ),
    html=(
      f'<span style="{MINION_STYLE}">中毒/醉酒</span>：'
      f'<span style="{MINION_STYLE}">中毒</span>的玩家会失去能力，但会认为自己仍具有能力，'
      "说书人会做出这些玩家仍然具有能力的行为。如果"
      f'<span style="{MINION_STYLE}">中毒</span>玩家的角色能力会给他提供信息，说书人可能会给出'
      f'<span style="{MINION_STYLE}">错误信息</span>，'
      f'<span style="{MINION_STYLE}">中毒</span>的玩家不会得知自己'
      f'<span style="{MINION_STYLE}">中毒</span>。'
      f'<span style="{MINION_STYLE}">醉酒</span>同理。'
    ),
    matches=lambda text: bool(
      "中毒" in text
      and "失去能力" in text
      and "如果中毒" in text
      and "错误信息" in text
      and re.search(r"[醉辞]酒.{0,4}同理", text)
    ),
    position_marker="失去能力",
  ),
  NoteDefinition(
    key="poison",
    label="中毒",
    text=(
      "中毒：中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
      "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。"
    ),
    html=(
      f'<span style="{MINION_STYLE}">中毒</span>：'
      f'<span style="{MINION_STYLE}">中毒</span>的玩家会失去能力，但会认为自己仍具有能力，'
      "说书人会做出这些玩家仍然具有能力的行为。如果"
      f'<span style="{MINION_STYLE}">中毒</span>玩家的角色能力会给他提供信息，说书人可能会给出'
      f'<span style="{MINION_STYLE}">错误信息</span>，'
      f'<span style="{MINION_STYLE}">中毒</span>的玩家不会得知自己'
      f'<span style="{MINION_STYLE}">中毒</span>。'
    ),
    matches=lambda text: bool(
      "中毒" in text
      and "失去能力" in text
      and "如果中毒" in text
      and "错误信息" in text
      and re.search(r"不会.{0,6}得知.{0,4}中毒", text)
      and not re.search(r"[醉辞]酒.{0,4}同理", text)
    ),
    position_marker="失去能力",
  ),
  NoteDefinition(
    key="not_first_night",
    label="*代表",
    text="*代表非首个夜晚",
    html="<strong>*代表</strong>非首个夜晚",
    matches=lambda text: "非首" in text and "夜晚" in text,
    position_marker="非首",
  ),
)

LEGACY_NOTE_TEXTS = {
  "*代表：非首个夜晚",
  "可能：某件事情“可能”发生，代表由说书人来决定该事情是否发生。",
  "疯狂：当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力地证明某件事情，如不这么做会受到惩罚。",
}


def is_standard_note_text(value: Any) -> bool:
  normalized = clean_text(value)
  return normalized in {
    *(clean_text(definition.text) for definition in NOTE_DEFINITIONS),
    *(clean_text(text) for text in LEGACY_NOTE_TEXTS),
  }


def clean_text(value: Any) -> str:
  return re.sub(r"\s+", "", str(value or ""))


def top_level_object_spans(raw: str) -> list[tuple[int, int]]:
  spans: list[tuple[int, int]] = []
  in_string = False
  escaped = False
  object_depth = 0
  object_start = -1
  for index, character in enumerate(raw):
    if in_string:
      if escaped:
        escaped = False
      elif character == "\\":
        escaped = True
      elif character == '"':
        in_string = False
      continue
    if character == '"':
      in_string = True
    elif character == "{":
      if object_depth == 0:
        object_start = index
      object_depth += 1
    elif character == "}" and object_depth:
      object_depth -= 1
      if object_depth == 0 and object_start >= 0:
        spans.append((object_start, index + 1))
        object_start = -1
  return spans


def meta_span(raw: str) -> tuple[int, int, dict[str, Any]]:
  for start, end in top_level_object_spans(raw):
    try:
      value = json.loads(raw[start:end])
    except json.JSONDecodeError:
      continue
    if isinstance(value, dict) and str(value.get("id", "")).strip() == "_meta":
      return start, end, value
  raise ValueError("JSON 中没有 _meta 对象")


def detected_notes(bottom_lines: list[str]) -> list[dict[str, str]]:
  text = clean_text("\n".join(bottom_lines))
  definitions = [definition for definition in NOTE_DEFINITIONS if definition.matches(text)]
  if any(definition.key == "poison_drunk" for definition in definitions):
    definitions = [definition for definition in definitions if definition.key != "poison"]
  definitions.sort(key=lambda definition: text.find(clean_text(definition.position_marker)))
  return [
    {
      "text": definition.text,
      "html": definition.html,
    }
    for definition in definitions
  ]


def roster_match_ratio(metadata: dict[str, Any]) -> float:
  required_count = int(metadata.get("ocr_required_character_count", 0) or 0)
  matched_count = int(metadata.get("ocr_character_matches", 0) or 0)
  return matched_count / required_count if required_count else 0.0


def process_metadata(
  metadata_path: Path,
  apply: bool,
  use_source_notes: bool,
) -> tuple[str, int, str]:
  metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
  source_notes: list[dict[str, str]] = []
  local_json = Path(str(metadata.get("local_json", "")))
  if local_json.exists():
    data = json.loads(local_json.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else []
    meta = next(
      (item for item in items if isinstance(item, dict) and item.get("id") == "_meta"),
      {},
    )
    for note in meta.get("notes", []):
      text = str(note.get("text", "") if isinstance(note, dict) else note).strip()
      if text:
        source_notes.append({"text": text})
  detected = detected_notes(metadata.get("ocr_bottom_text", [])) if use_source_notes else []
  existing = [
    check for check in metadata.get("ocr_note_checks", [])
    if isinstance(check, dict) and str(check.get("text", "")).strip()
  ]
  checks_by_text = {str(check["text"]).strip(): check for check in existing}
  for note in [*source_notes, *detected]:
    checks_by_text.setdefault(note["text"].strip(), {"text": note["text"].strip()})
  checks = list(checks_by_text.values())
  if apply and checks != existing:
    metadata["ocr_note_checks"] = checks
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  added_count = len(checks) - len(existing)
  message = "" if checks else "阵容匹配度不足" if not use_source_notes else "源图没有标准说明"
  return str(metadata.get("script_name", metadata_path.parent.name)), added_count, message


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--audit-root", type=Path, default=Path("bilibili_script_audit"))
  parser.add_argument("--apply", action="store_true", help="Store detected text in existing audit status files.")
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  changed_scripts = 0
  note_count = 0
  review_messages: list[str] = []
  best_metadata_by_json: dict[str, tuple[float, Path]] = {}
  for metadata_path in sorted((args.audit_root / "剧本").glob("*/核对状态.json")):
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    local_json = str(metadata.get("local_json", ""))
    if not local_json:
      continue
    score = roster_match_ratio(metadata)
    current = best_metadata_by_json.get(local_json)
    if current is None or score > current[0]:
      best_metadata_by_json[local_json] = (score, metadata_path)
  for score, metadata_path in sorted(best_metadata_by_json.values(), key=lambda value: str(value[1])):
    name, count, message = process_metadata(metadata_path, args.apply, score >= 0.8)
    if count:
      changed_scripts += 1
      note_count += count
      print(f"{'记录' if args.apply else '待记录'}：{name}（{count} 条）")
    elif message and message != "源图没有标准说明":
      review_messages.append(f"{name}：{message}")
  print(f"剧本 {changed_scripts} 个，说明 {note_count} 条。")
  if review_messages:
    print("需要人工处理：")
    for message in review_messages:
      print(f"- {message}")


if __name__ == "__main__":
  main()
