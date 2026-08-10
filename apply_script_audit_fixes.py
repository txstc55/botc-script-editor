#!/usr/bin/env python3
"""Apply reviewed, script-specific role replacements without reserializing files."""

from __future__ import annotations

import argparse
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


def top_level_object_spans(raw: str) -> list[tuple[int, int]]:
  spans: list[tuple[int, int]] = []
  in_string = False
  escaped = False
  depth = 0
  start = -1
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
      if depth == 0:
        start = index
      depth += 1
    elif character == "}" and depth:
      depth -= 1
      if depth == 0 and start >= 0:
        spans.append((start, index + 1))
        start = -1
  return spans


def parsed_objects(raw: str) -> list[tuple[int, int, dict[str, Any]]]:
  objects: list[tuple[int, int, dict[str, Any]]] = []
  for start, end in top_level_object_spans(raw):
    value = json.loads(raw[start:end])
    if isinstance(value, dict):
      objects.append((start, end, value))
  return objects


def source_role(source_path: Path, name: str, team: str) -> dict[str, Any]:
  data = json.loads(source_path.read_text(encoding="utf-8"))
  if not isinstance(data, list):
    raise ValueError(f"角色来源不是数组：{source_path}")
  matches = [
    item for item in data
    if isinstance(item, dict) and item.get("name") == name and item.get("team") == team
  ]
  if len(matches) != 1:
    raise ValueError(f"角色来源不是唯一结果：{source_path}：{team}/{name}")
  return matches[0]


def formatted_object(value: dict[str, Any], base_indent: str) -> str:
  lines = json.dumps(value, ensure_ascii=False, indent=2).splitlines()
  return lines[0] + "\n" + "\n".join(base_indent + line for line in lines[1:])


def object_identity(value: dict[str, Any]) -> tuple[str, str]:
  return str(value.get("name", "")), str(value.get("team", ""))


@lru_cache(maxsize=1)
def database_rows() -> dict[tuple[str, str], list[dict[str, str]]]:
  from extract_audit_role_replacements import character_rows

  return character_rows()


def database_role(spec: dict[str, Any]) -> dict[str, Any]:
  entry = spec.get("entry")
  if isinstance(entry, dict):
    return entry

  from audit_bilibili_scripts import clean_space
  from extract_audit_role_replacements import row_entry

  name = clean_space(spec.get("name"))
  team = clean_space(spec.get("team"))
  expected_ability = clean_space(spec.get("ability"))
  rows = database_rows().get((name, team), [])
  if expected_ability:
    rows = [row for row in rows if clean_space(row.get("ability")) == expected_ability]
  if not rows:
    raise ValueError(f"角色数据库中找不到：{team}/{name}")
  row = max(rows, key=lambda value: int(value.get("occurrence_count", 0) or 0))
  role = row_entry(row)
  overrides = spec.get("overrides")
  if isinstance(overrides, dict):
    role.update(overrides)
  return role


def rebuild_full_roster(raw: str, roster: dict[str, Any]) -> tuple[str, bool]:
  data = json.loads(raw)
  if not isinstance(data, list):
    raise ValueError("剧本 JSON 不是顶层数组")
  meta = [
    item for item in data
    if isinstance(item, dict) and str(item.get("id", "")).strip() == "_meta"
  ]
  if len(meta) != 1:
    raise ValueError("剧本 _meta 不是唯一结果")
  jinxes = [
    item for item in data
    if isinstance(item, dict) and "jinx" in clean_team(item.get("team"))
  ]
  rebuilt = [meta[0], *(database_role(spec) for spec in roster.get("entries", [])), *jinxes]
  if data == rebuilt:
    return raw, False
  return json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", True


def apply_fix(raw: str, fix: dict[str, Any]) -> tuple[str, list[str]]:
  changes: list[str] = []
  for removal in fix.get("removals", []):
    removal_id = str(removal.get("id", "")).strip()
    if removal_id:
      matches = [item for item in parsed_objects(raw) if str(item[2].get("id", "")).strip() == removal_id]
      label = removal_id
    else:
      identity = (removal["name"], removal["team"])
      matches = [item for item in parsed_objects(raw) if object_identity(item[2]) == identity]
      label = identity[0]
    if not matches:
      continue
    if len(matches) != 1:
      raise ValueError(f"待移除角色不是唯一结果：{label}")
    start, end, _ = matches[0]
    line_start = raw.rfind("\n", 0, start) + 1
    trailing = re.match(r",[ \t]*\r?\n", raw[end:])
    if trailing:
      raw = raw[:line_start] + raw[end + trailing.end():]
    else:
      prefix = raw[:line_start].rstrip()
      raw = prefix.removesuffix(",") + raw[end:]
    changes.append(f"移除 {label}")

  for replacement in fix.get("replacements", []):
    old_identity = (replacement["old_name"], replacement["old_team"])
    new_role = replacement.get("entry")
    if not isinstance(new_role, dict):
      new_role = source_role(
        Path(replacement["source_json"]),
        replacement["new_name"],
        replacement["new_team"],
      )
    objects = parsed_objects(raw)
    old_matches = [item for item in objects if object_identity(item[2]) == old_identity]
    new_matches = [item for item in objects if object_identity(item[2]) == object_identity(new_role)]
    if not old_matches and new_matches:
      continue
    if len(old_matches) != 1:
      raise ValueError(f"待替换角色不是唯一结果：{old_identity[1]}/{old_identity[0]}")
    if old_matches[0][2] == new_role:
      continue
    start, end, _ = old_matches[0]
    line_start = raw.rfind("\n", 0, start) + 1
    base_indent = raw[line_start:start]
    raw = raw[:start] + formatted_object(new_role, base_indent) + raw[end:]
    changes.append(f"{old_identity[0]} -> {new_role['name']}")

  for addition in fix.get("additions", []):
    new_role = addition.get("entry")
    explicit_entry = isinstance(new_role, dict) or isinstance(addition.get("overrides"), dict)
    if not isinstance(new_role, dict):
      if addition.get("source_json"):
        new_role = source_role(
          Path(addition["source_json"]),
          addition["name"],
          addition["team"],
        )
      else:
        new_role = database_role(addition)
    matches = [
      item for item in parsed_objects(raw)
      if object_identity(item[2]) == object_identity(new_role)
    ]
    if matches:
      if len(matches) != 1:
        raise ValueError(f"已存在角色不是唯一结果：{new_role['name']}")
      if matches[0][2] == new_role or not explicit_entry:
        continue
      start, end, _ = matches[0]
      line_start = raw.rfind("\n", 0, start) + 1
      base_indent = raw[line_start:start]
      raw = raw[:start] + formatted_object(new_role, base_indent) + raw[end:]
      changes.append(f"更新 {new_role['name']}")
      continue
    before = addition.get("before")
    if isinstance(before, dict):
      identity = (str(before.get("name", "")), str(before.get("team", "")))
      matches = [item for item in parsed_objects(raw) if object_identity(item[2]) == identity]
      if len(matches) != 1:
        raise ValueError(f"新增角色定位目标不是唯一结果：{identity[1]}/{identity[0]}")
      start, _, _ = matches[0]
      line_start = raw.rfind("\n", 0, start) + 1
      base_indent = raw[line_start:start]
      role_text = formatted_object(new_role, base_indent)
      raw = raw[:line_start] + f"{base_indent}{role_text},\n" + raw[line_start:]
      changes.append(f"新增 {new_role['name']}")
      continue
    closing_index = raw.rfind("]")
    if closing_index < 0:
      raise ValueError("剧本 JSON 没有顶层数组结尾")
    prefix = raw[:closing_index].rstrip()
    separator = "" if prefix.endswith("[") else ","
    role_text = formatted_object(new_role, "  ")
    raw = f"{prefix}{separator}\n  {role_text}\n{raw[closing_index:]}"
    changes.append(f"新增 {new_role['name']}")

  for roster in fix.get("team_rosters", []):
    team = roster["team"]
    entries = roster["entries"]
    objects = parsed_objects(raw)
    matches = [
      (index, start, end, value)
      for index, (start, end, value) in enumerate(objects)
      if clean_team(value.get("team")) == team
    ]
    if not matches:
      raise ValueError(f"剧本中没有阵营：{team}")
    current_entries = [item[3] for item in matches]
    if current_entries == entries:
      continue
    if len(matches) != len(entries):
      raise ValueError(f"阵营角色数量不一致：{team}")
    for (_, start, end, _), entry in reversed(list(zip(matches, entries))):
      line_start = raw.rfind("\n", 0, start) + 1
      base_indent = raw[line_start:start]
      raw = raw[:start] + formatted_object(entry, base_indent) + raw[end:]
    changes.append(f"重建 {team} 阵容")

  meta_updates = fix.get("meta_updates")
  if isinstance(meta_updates, dict):
    matches = [
      item for item in parsed_objects(raw)
      if str(item[2].get("id", "")).strip() == "_meta"
    ]
    if len(matches) != 1:
      raise ValueError("剧本 _meta 不是唯一结果")
    start, end, meta = matches[0]
    changed_fields = [
      key for key, value in meta_updates.items()
      if meta.get(key) != value
    ]
    if changed_fields:
      meta.update(meta_updates)
      line_start = raw.rfind("\n", 0, start) + 1
      base_indent = raw[line_start:start]
      raw = raw[:start] + formatted_object(meta, base_indent) + raw[end:]
      changes.append(f"更新剧本信息 {', '.join(changed_fields)}")

  notes = fix.get("meta_notes", [])
  if notes:
    matches = [
      item for item in parsed_objects(raw)
      if str(item[2].get("id", "")).strip() == "_meta"
    ]
    if len(matches) != 1:
      raise ValueError("剧本 _meta 不是唯一结果")
    start, end, meta = matches[0]
    existing_notes = meta.setdefault("notes", [])
    existing_texts = {
      str(item.get("text", "")).strip() if isinstance(item, dict) else str(item).strip()
      for item in existing_notes
    }
    new_notes = [note for note in notes if note.get("text", "").strip() not in existing_texts]
    if new_notes:
      existing_notes.extend(new_notes)
      line_start = raw.rfind("\n", 0, start) + 1
      base_indent = raw[line_start:start]
      raw = raw[:start] + formatted_object(meta, base_indent) + raw[end:]
      changes.append(f"新增说明 {len(new_notes)} 条")
  full_roster = fix.get("full_roster")
  if isinstance(full_roster, dict):
    raw, changed = rebuild_full_roster(raw, full_roster)
    if changed:
      changes.append("重建完整阵容")
  return raw, changes


def clean_team(value: Any) -> str:
  return str(value or "").strip().lower()


def reviewed_role_fixes(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
  candidate_value = manifest.get("role_candidate_file")
  reviews = manifest.get("reviewed_role_replacements", [])
  if not candidate_value or not reviews:
    return []
  candidate_path = manifest_path.parent / candidate_value
  candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
  fixes_by_target: dict[str, dict[str, Any]] = {}
  for review in reviews:
    matches = [
      candidate for candidate in candidates
      if candidate.get("script_name") == review.get("script_name")
      and candidate.get("old_name") == review.get("old_name")
      and candidate.get("new_name") == review.get("new_name")
    ]
    if not matches:
      continue
    if len(matches) > 1:
      raise ValueError(f"审核角色候选不是唯一结果：{review}")
    candidate = matches[0]
    entry = dict(candidate["entry"])
    if "ability" in review:
      entry["ability"] = review["ability"]
    target = candidate["local_json"]
    fix = fixes_by_target.setdefault(target, {
      "source": candidate["reference_image"],
      "targets": [target],
      "replacements": [],
    })
    fix["replacements"].append({
      "old_name": review["old_name"],
      "old_team": candidate["team"],
      "entry": entry,
    })
  return list(fixes_by_target.values())


def reviewed_roster_fixes(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
  candidate_value = manifest.get("roster_candidate_file")
  reviews = manifest.get("reviewed_team_rosters", [])
  if not candidate_value or not reviews:
    return []
  candidate_path = manifest_path.parent / candidate_value
  candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
  fixes_by_target: dict[str, dict[str, Any]] = {}
  for review in reviews:
    matches = [
      candidate for candidate in candidates
      if candidate.get("script_name") == review.get("script_name")
      and candidate.get("team") == review.get("team")
    ]
    if not matches:
      continue
    if len(matches) > 1:
      raise ValueError(f"审核阵容候选不是唯一结果：{review}")
    candidate = matches[0]
    if candidate.get("unresolved_names"):
      raise ValueError(f"审核阵容仍有未解析角色：{review}")
    target = candidate["local_json"]
    fix = fixes_by_target.setdefault(target, {
      "source": candidate["reference_image"],
      "targets": [target],
      "team_rosters": [],
    })
    fix["team_rosters"].append({
      "team": review["team"],
      "entries": candidate["entries"],
    })
  return list(fixes_by_target.values())


def reviewed_cross_roster_fixes(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
  candidate_value = manifest.get("cross_roster_candidate_file")
  reviews = manifest.get("reviewed_cross_team_rosters", [])
  if not candidate_value or not reviews:
    return []
  candidate_path = manifest_path.parent / candidate_value
  candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
  fixes_by_target: dict[str, dict[str, Any]] = {}
  for review in reviews:
    matches = [
      candidate for candidate in candidates
      if candidate.get("script_name") == review.get("script_name")
      and candidate.get("team") == review.get("team")
    ]
    if not matches:
      continue
    if len(matches) > 1:
      raise ValueError(f"审核跨阵营候选不是唯一结果：{review}")
    candidate = matches[0]
    if candidate.get("unresolved_names"):
      raise ValueError(f"审核跨阵营候选仍有未解析角色：{review}")
    target = candidate["local_json"]
    fix = fixes_by_target.setdefault(target, {
      "source": candidate["reference_image"],
      "targets": [target],
      "removals": [],
      "additions": [],
      "team_rosters": [],
    })
    fix["removals"].extend(
      {"name": name, "team": review["team"]}
      for name in candidate["removed_names"]
    )
    fix["additions"].extend(
      {"entry": addition["entry"]} for addition in candidate["additions"]
    )
    fix["team_rosters"].append({
      "team": review["team"],
      "entries": candidate["entries"],
    })
  return list(fixes_by_target.values())


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--manifest", type=Path, default=Path("script_audit_fixes.json"))
  parser.add_argument("--apply", action="store_true")
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
  fixes = manifest.get("fixes", []) if isinstance(manifest, dict) else []
  fixes = [
    *fixes,
    *reviewed_role_fixes(manifest, args.manifest),
    *reviewed_roster_fixes(manifest, args.manifest),
    *reviewed_cross_roster_fixes(manifest, args.manifest),
  ]
  changed_files = 0
  for fix in fixes:
    for target_value in fix.get("targets", []):
      target = Path(target_value)
      raw = target.read_text(encoding="utf-8")
      updated, changes = apply_fix(raw, fix)
      if not changes:
        continue
      changed_files += 1
      print(f"{'写入' if args.apply else '待写入'}：{target}：{'; '.join(changes)}")
      if args.apply:
        target.write_text(updated, encoding="utf-8")
  print(f"剧本文件 {changed_files} 个。")


if __name__ == "__main__":
  main()
