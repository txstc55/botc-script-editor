#!/usr/bin/env python3
"""Add standard bottom-of-board explanations confirmed by source-image OCR."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


MINION_STYLE = "color: rgb(143, 23, 1); font-weight: 900;"
TRAVELER_STYLE = "color: rgb(103, 14, 171); font-weight: 900;"


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
    text="可能：某件事情“可能”发生，代表由说书人来决定该事情是否发生。",
    html=(
      f'<span style="{TRAVELER_STYLE}">可能</span>：'
      "某件事情“可能”发生，代表由说书人来决定该事情是否发生。"
    ),
    matches=lambda text: bool(re.search(r"某件事情.{0,3}可能.{0,3}发生", text)),
    position_marker="某件事情",
  ),
  NoteDefinition(
    key="madness",
    label="疯狂",
    text=(
      "疯狂：当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力地证明某件事情，"
      "如不这么做会受到惩罚。"
    ),
    html=(
      f'<span style="{TRAVELER_STYLE}">疯狂</span>：'
      "当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力地证明某件事情，"
      "如不这么做会受到惩罚。"
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
      "中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
      "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。"
      "醉酒同理。"
    ),
    matches=lambda text: (
      "中毒" in text and "醉酒" in text and "失去能力" in text and
      ("醉酒同理" in text or "中毒/醉酒" in text)
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
      "中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
      "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。"
    ),
    matches=lambda text: "中毒" in text and "失去能力" in text and "醉酒" not in text,
    position_marker="失去能力",
  ),
  NoteDefinition(
    key="not_first_night",
    label="*代表",
    text="*代表：非首个夜晚",
    html="<strong>*代表</strong>：非首个夜晚",
    matches=lambda text: "非首" in text and "夜晚" in text,
    position_marker="非首",
  ),
)


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


def formatted_notes_property(notes: list[dict[str, str]], property_indent: str) -> str:
  serialized = json.dumps(notes, ensure_ascii=False, indent=2)
  serialized = serialized.replace("\n", f"\n{property_indent}")
  return f'{property_indent}"notes": {serialized}'


def insert_notes(raw: str, notes: list[dict[str, str]]) -> str:
  start, end, meta = meta_span(raw)
  if meta.get("notes"):
    raise ValueError("_meta.notes 已存在，请人工合并")
  object_text = raw[start:end]
  property_match = re.search(r"\n([ \t]+)\"", object_text)
  property_indent = property_match.group(1) if property_match else "  "
  closing_match = re.search(r"\n([ \t]*)\}\s*$", object_text)
  closing_indent = closing_match.group(1) if closing_match else ""
  closing_index = object_text.rfind("}")
  prefix = object_text[:closing_index].rstrip()
  separator = "" if prefix.endswith("{") else ","
  replacement = (
    f"{prefix}{separator}\n"
    f"{formatted_notes_property(notes, property_indent)}\n"
    f"{closing_indent}}}"
  )
  return raw[:start] + replacement + raw[end:]


def replace_notes(raw: str, notes: list[dict[str, str]]) -> str:
  start, end, meta = meta_span(raw)
  if not isinstance(meta.get("notes"), list):
    return insert_notes(raw, notes)
  object_text = raw[start:end]
  key_match = re.search(r'"notes"\s*:\s*', object_text)
  if not key_match:
    raise ValueError("无法定位 _meta.notes")
  array_start = object_text.find("[", key_match.end())
  if array_start < 0:
    raise ValueError("_meta.notes 不是数组")
  in_string = False
  escaped = False
  depth = 0
  array_end = -1
  for index in range(array_start, len(object_text)):
    character = object_text[index]
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
    elif character == "[":
      depth += 1
    elif character == "]":
      depth -= 1
      if depth == 0:
        array_end = index + 1
        break
  if array_end < 0:
    raise ValueError("_meta.notes 数组没有结束")
  line_start = object_text.rfind("\n", 0, key_match.start()) + 1
  property_indent = object_text[line_start:key_match.start()]
  serialized = json.dumps(notes, ensure_ascii=False, indent=2)
  serialized = serialized.replace("\n", f"\n{property_indent}")
  replacement = object_text[:array_start] + serialized + object_text[array_end:]
  return raw[:start] + replacement + raw[end:]


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
  local_json = Path(str(metadata.get("local_json", "")))
  if not local_json.exists():
    return str(metadata.get("script_name", metadata_path.parent.name)), 0, "没有本地 JSON"
  notes = detected_notes(metadata.get("ocr_bottom_text", [])) if use_source_notes else []
  raw = local_json.read_text(encoding="utf-8")
  try:
    _, _, meta = meta_span(raw)
  except ValueError as error:
    return str(metadata.get("script_name", local_json.stem)), 0, str(error)
  existing = meta.get("notes", [])
  if existing:
    canonical_texts = {
      clean_text(definition.text) for definition in NOTE_DEFINITIONS
    }
    preserved = [
      note for note in existing
      if not isinstance(note, dict) or clean_text(note.get("text")) not in canonical_texts
    ]
    reconciled = [*preserved, *notes]
    if reconciled == existing:
      message = "说明已存在" if notes else "源图没有标准说明"
      return str(metadata.get("script_name", local_json.stem)), 0, message
    if apply:
      local_json.write_text(replace_notes(raw, reconciled), encoding="utf-8")
    if not notes:
      reason = "阵容匹配度不足，移除脚本生成的标准说明" if not use_source_notes else "移除源图未包含的标准说明"
      return str(metadata.get("script_name", local_json.stem)), 0, reason
    return str(metadata.get("script_name", local_json.stem)), len(notes), ""
  if not notes:
    message = "阵容匹配度不足" if not use_source_notes else "源图没有标准说明"
    return str(metadata.get("script_name", local_json.stem)), 0, message
  if apply:
    local_json.write_text(insert_notes(raw, notes), encoding="utf-8")
  return str(metadata.get("script_name", local_json.stem)), len(notes), ""


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--audit-root", type=Path, default=Path("bilibili_script_audit"))
  parser.add_argument("--apply", action="store_true")
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
      print(f"{'写入' if args.apply else '待写入'}：{name}（{count} 条）")
    elif "移除" in message:
      changed_scripts += 1
      print(f"{'写入' if args.apply else '待写入'}：{name}（{message}）")
    elif message not in {"源图没有标准说明", "说明已存在"}:
      review_messages.append(f"{name}：{message}")
  print(f"剧本 {changed_scripts} 个，说明 {note_count} 条。")
  if review_messages:
    print("需要人工处理：")
    for message in review_messages:
      print(f"- {message}")


if __name__ == "__main__":
  main()
