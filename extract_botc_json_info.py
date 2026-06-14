#!/usr/bin/env python3
"""Extract BOTC character variants and jinx interaction rules from script JSONs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = "all_jsons"
DEFAULT_CHARACTERS_OUTPUT = "botc_characters.csv"
DEFAULT_JINXES_OUTPUT = "botc_jinxes.csv"
DEFAULT_ISSUES_OUTPUT = "botc_extraction_issues.csv"
JOINER = " || "

EXPECTED_TEAM_VALUES = {
  "fabled",
  "townsfolk",
  "outsider",
  "outsiders",
  "minion",
  "minions",
  "demon",
  "demons",
  "traveler",
  "travelers",
}

TEAM_NORMALIZATION = {
  "fabled": "fabled",
  "townsfolk": "townsfolk",
  "outsider": "outsider",
  "outsiders": "outsider",
  "minion": "minion",
  "minions": "minion",
  "demon": "demon",
  "demons": "demon",
  "traveler": "traveler",
  "travelers": "traveler",
  "traveller": "traveler",
  "travellers": "traveler",
}

VARIANT_VALUE_FIELDS = [
  "team",
  "normalized_team",
  "unexpected_team",
  "ability",
  "image",
  "flavor",
  "setup",
  "first_night_order",
  "first_night_reminder",
  "other_night_order",
  "other_night_reminder",
  "reminders",
  "reminders_global",
  "jinx_targets",
  "jinx_target_count",
  "rule_source_character",
  "rule_target_id",
  "rule_target_name",
  "target_detection_notes",
]
JINX_VARIANT_VALUE_FIELDS = [
  "team",
  "ability",
]

CHARACTER_COLUMNS = [
  "name",
  "variant_index",
  "variants_for_name",
  "occurrence_count",
  "team",
  "normalized_team",
  "unexpected_team",
  "ability",
  "image",
  "first_night_order",
  "first_night_reminder",
  "missing_first_night_reminder",
  "missing_first_night_reminder_sources",
  "other_night_order",
  "other_night_reminder",
  "missing_other_night_reminder",
  "missing_other_night_reminder_sources",
  "reminders",
  "reminders_global",
  "setup",
  "flavor",
  "raw_keys",
  "source_script_count",
  "source_scripts",
  "source_author_count",
  "source_authors",
  "source_file_count",
  "source_files",
  "source_ids",
  "issue_notes",
]

JINX_COLUMNS = [
  "name",
  "variant_index",
  "variants_for_name",
  "occurrence_count",
  "team",
  "ability",
  "jinx_targets",
  "jinx_target_count",
  "target_detection_notes",
  "rule_source_character",
  "rule_target_id",
  "rule_target_name",
  "source_script_count",
  "source_scripts",
  "source_author_count",
  "source_authors",
  "source_file_count",
  "source_files",
  "source_ids",
  "issue_notes",
]

ISSUE_COLUMNS = [
  "issue_type",
  "value",
  "count",
  "sample_names",
  "sample_files",
  "details",
]


@dataclass
class ScriptData:
  path: Path
  rel_path: str
  entries: list[Any]
  script_name: str
  author: str
  id_to_name: dict[str, str]
  character_names: set[str]


def clean_text(value: Any) -> str:
  if value is None:
    return ""
  if isinstance(value, str):
    return re.sub(r"\s+", " ", value).strip()
  if isinstance(value, bool):
    return "true" if value else "false"
  if isinstance(value, (int, float)):
    if isinstance(value, float) and value.is_integer():
      return str(int(value))
    return str(value)
  return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def list_text(value: Any) -> str:
  if not isinstance(value, list):
    return clean_text(value)
  values = sorted({clean_text(item) for item in value if clean_text(item)})
  return JOINER.join(values)


def joined(values: set[str] | list[str]) -> str:
  if isinstance(values, set):
    return JOINER.join(sorted(values))
  return JOINER.join(values)


def split_joined(value: str) -> set[str]:
  return {part.strip() for part in value.split(JOINER) if part.strip()}


def merge_joined_values(left: str, right: str) -> str:
  values = split_joined(left) | split_joined(right)
  return JOINER.join(sorted(values))


def to_number(value: Any) -> float:
  if value is None or value == "":
    return 0.0
  if isinstance(value, bool):
    return 1.0 if value else 0.0
  try:
    return float(value)
  except (TypeError, ValueError):
    return 0.0


def has_night_order(value: Any) -> bool:
  return to_number(value) > 0


def setup_text(value: Any) -> str:
  text = clean_text(value).lower()
  if text in ("", "false", "null", "none"):
    return "0"
  if text == "true":
    return "1"
  try:
    return "1" if float(text) > 0 else "0"
  except ValueError:
    pass
  return text


def is_jinx_team(team: Any) -> bool:
  return "jinx" in clean_text(team).lower()


def normalized_team(team: Any) -> str:
  text = clean_text(team)
  lower = text.lower()
  if not text:
    return ""
  if is_jinx_team(text):
    return "jinx"
  return TEAM_NORMALIZATION.get(lower, text)


def is_unexpected_team(team: Any) -> bool:
  text = clean_text(team)
  if not text or is_jinx_team(text):
    return False
  return text.lower() not in EXPECTED_TEAM_VALUES


def is_meta_entry(item: Any, index: int) -> bool:
  if not isinstance(item, dict):
    return False
  if item.get("id") == "_meta":
    return True
  return (
    index == 0
    and "team" not in item
    and "ability" not in item
    and any(key in item for key in ("name", "author", "logo", "description", "almanac"))
  )


def reminder_value(item: dict[str, Any], primary_key: str, fallback_keys: tuple[str, ...]) -> str:
  if primary_key in item:
    return clean_text(item.get(primary_key))
  for key in fallback_keys:
    if key in item:
      return clean_text(item.get(key))
  return ""


def read_json_file(path: Path, fetch_url_files: bool) -> tuple[Any | None, str | None]:
  text = path.read_text(encoding="utf-8-sig")
  stripped = text.strip()
  if stripped.startswith(("http://", "https://")):
    if not fetch_url_files:
      return None, "url_file_not_loaded"
    with urllib.request.urlopen(stripped, timeout=30) as response:
      payload = response.read().decode("utf-8-sig")
    return json.loads(payload), None
  try:
    return json.loads(text), None
  except json.JSONDecodeError as exc:
    return None, f"json_decode_error: {exc}"


def entries_from_data(data: Any) -> tuple[list[Any], str | None]:
  if isinstance(data, list):
    return data, None
  if isinstance(data, dict):
    for key in ("characters", "roles", "script"):
      value = data.get(key)
      if isinstance(value, list):
        return value, None
    return [data], "top_level_dict_without_known_list"
  return [], f"unsupported_top_level_type: {type(data).__name__}"


def load_scripts(input_dir: Path, fetch_url_files: bool) -> tuple[list[ScriptData], list[dict[str, str]]]:
  scripts: list[ScriptData] = []
  issues: list[dict[str, str]] = []

  for path in sorted(input_dir.rglob("*.json")):
    rel_path = path.relative_to(input_dir.parent).as_posix()
    try:
      data, issue = read_json_file(path, fetch_url_files)
    except Exception as exc:  # noqa: BLE001
      data, issue = None, f"read_error: {type(exc).__name__}: {exc}"

    if issue:
      issues.append({
        "issue_type": issue.split(":", 1)[0],
        "value": rel_path,
        "count": "1",
        "sample_names": "",
        "sample_files": rel_path,
        "details": issue,
      })
    if data is None:
      continue

    entries, entry_issue = entries_from_data(data)
    if entry_issue:
      issues.append({
        "issue_type": entry_issue.split(":", 1)[0],
        "value": rel_path,
        "count": "1",
        "sample_names": "",
        "sample_files": rel_path,
        "details": entry_issue,
      })

    meta = next(
      (item for index, item in enumerate(entries) if is_meta_entry(item, index)),
      {},
    )
    script_name = clean_text(meta.get("name")) or path.stem
    author = clean_text(meta.get("author"))
    id_to_name: dict[str, str] = {}
    character_names: set[str] = set()
    for item in entries:
      if not isinstance(item, dict):
        continue
      role_id = clean_text(item.get("id"))
      name = clean_text(item.get("name"))
      if role_id and name:
        id_to_name[role_id] = name
      if name and not is_jinx_team(item.get("team")):
        character_names.add(name)

    scripts.append(ScriptData(
      path=path,
      rel_path=rel_path,
      entries=entries,
      script_name=script_name,
      author=author,
      id_to_name=id_to_name,
      character_names=character_names,
    ))

  return scripts, issues


def build_global_id_map(scripts: list[ScriptData]) -> dict[str, set[str]]:
  global_ids: dict[str, set[str]] = defaultdict(set)
  for script in scripts:
    for role_id, name in script.id_to_name.items():
      global_ids[role_id].add(name)
  return global_ids


def resolve_jinx_target_name(target_id: str, script: ScriptData, global_ids: dict[str, set[str]]) -> str:
  if target_id in script.id_to_name:
    return script.id_to_name[target_id]
  names = global_ids.get(target_id, set())
  if len(names) == 1:
    return next(iter(names))
  return ""


def split_interaction_name(name: str) -> list[str]:
  return [part.strip() for part in re.split(r"\s*[&＆]\s*", name) if part.strip()]


def detect_play_jinx_targets(script: ScriptData, *texts: str) -> list[str]:
  haystack = "\n".join(text for text in texts if text)
  if not haystack:
    return []
  return [
    name
    for name in sorted(script.character_names, key=lambda item: (-len(item), item))
    if name and name in haystack
  ]


def source_label(script: ScriptData, item: dict[str, Any]) -> str:
  role_id = clean_text(item.get("id"))
  if role_id:
    return f"{script.rel_path}#{role_id}"
  return script.rel_path


def variant_key(record_type: str, name: str, values: dict[str, str]) -> tuple[str, str, tuple[tuple[str, str], ...]]:
  fields = JINX_VARIANT_VALUE_FIELDS if record_type == "interaction_rule" else VARIANT_VALUE_FIELDS
  return (
    record_type,
    name,
    tuple((field, values.get(field, "")) for field in fields),
  )


def make_variant(record_type: str, name: str, values: dict[str, str]) -> dict[str, Any]:
  agg: dict[str, Any] = {
    "record_type": record_type,
    "name": name,
    "values": values,
    "occurrence_count": 0,
    "variant_index": 1,
    "variants_for_name": 1,
    "raw_keys": set(),
    "source_scripts": set(),
    "source_authors": set(),
    "source_files": set(),
    "source_ids": set(),
    "issue_notes": set(),
    "missing_first_night_reminder_sources": [],
    "missing_other_night_reminder_sources": [],
  }
  return agg


def add_common_source_data(agg: dict[str, Any], script: ScriptData, item: dict[str, Any]) -> None:
  agg["occurrence_count"] += 1
  agg["source_scripts"].add(script.script_name)
  if script.author:
    agg["source_authors"].add(script.author)
  agg["source_files"].add(script.rel_path)
  agg["source_ids"].add(source_label(script, item))
  ignored_raw_keys = {"id", "edition", "name_id", "name_eng", "sch_team"}
  for key in item:
    if key in ignored_raw_keys:
      continue
    agg["raw_keys"].add(key)


def merge_jinx_values(agg: dict[str, Any], values: dict[str, str]) -> None:
  existing = agg["values"]
  for field in (
    "jinx_targets",
    "target_detection_notes",
    "rule_source_character",
    "rule_target_id",
    "rule_target_name",
  ):
    existing[field] = merge_joined_values(existing.get(field, ""), values.get(field, ""))
  existing["jinx_target_count"] = str(len(split_joined(existing.get("jinx_targets", ""))))


def character_values(item: dict[str, Any]) -> dict[str, str]:
  team = clean_text(item.get("team"))
  first_reminder = reminder_value(item, "firstNightReminder", ("firstReminder",))
  other_reminder = reminder_value(item, "otherNightReminder", ("ogherNightReminder",))
  return {
    "team": team,
    "normalized_team": normalized_team(team),
    "unexpected_team": team if is_unexpected_team(team) else "",
    "ability": clean_text(item.get("ability")),
    "image": clean_text(item.get("image")),
    "flavor": clean_text(item.get("flavor")),
    "setup": setup_text(item.get("setup")),
    "first_night_order": clean_text(item.get("firstNight")),
    "first_night_reminder": first_reminder,
    "other_night_order": clean_text(item.get("otherNight")),
    "other_night_reminder": other_reminder,
    "reminders": list_text(item.get("reminders")),
    "reminders_global": list_text(item.get("remindersGlobal")),
    "jinx_targets": "",
    "jinx_target_count": "",
    "rule_source_character": "",
    "rule_target_id": "",
    "rule_target_name": "",
    "target_detection_notes": "",
  }


def add_character(variants: dict[Any, dict[str, Any]], script: ScriptData, item: dict[str, Any]) -> None:
  name = clean_text(item.get("name"))
  if not name:
    return

  values = character_values(item)
  key = variant_key("character", name, values)
  agg = variants.setdefault(key, make_variant("character", name, values))
  add_common_source_data(agg, script, item)

  if values["unexpected_team"]:
    agg["issue_notes"].add(f"unexpected_team:{values['unexpected_team']}")
  if has_night_order(item.get("firstNight")) and not values["first_night_reminder"]:
    agg["issue_notes"].add("missing_first_night_reminder")
    agg["missing_first_night_reminder_sources"].append(source_label(script, item))
  if has_night_order(item.get("otherNight")) and not values["other_night_reminder"]:
    agg["issue_notes"].add("missing_other_night_reminder")
    agg["missing_other_night_reminder_sources"].append(source_label(script, item))


def interaction_values(
  script: ScriptData,
  name: str,
  team: str,
  ability: str,
  source_character: str = "",
  target_id: str = "",
  target_name: str = "",
) -> dict[str, str]:
  targets = detect_play_jinx_targets(script, name, ability, source_character, target_name)
  notes = []
  if not targets:
    notes.append("no_play_character_names_found")

  return {
    "team": team,
    "normalized_team": "jinx",
    "unexpected_team": "",
    "ability": ability,
    "image": "",
    "flavor": "",
    "setup": "",
    "first_night_order": "",
    "first_night_reminder": "",
    "other_night_order": "",
    "other_night_reminder": "",
    "reminders": "",
    "reminders_global": "",
    "jinx_targets": JOINER.join(targets),
    "jinx_target_count": str(len(targets)),
    "rule_source_character": source_character,
    "rule_target_id": target_id,
    "rule_target_name": target_name,
    "target_detection_notes": JOINER.join(notes),
  }


def add_interaction(
  variants: dict[Any, dict[str, Any]],
  script: ScriptData,
  item: dict[str, Any],
  name: str,
  team: str,
  ability: str,
  source_character: str = "",
  target_id: str = "",
  target_name: str = "",
) -> None:
  if not name:
    name = f"unnamed jinx {source_label(script, item)}"

  values = interaction_values(
    script=script,
    name=name,
    team=team,
    ability=ability,
    source_character=source_character,
    target_id=target_id,
    target_name=target_name,
  )
  key = variant_key("interaction_rule", name, values)
  agg = variants.get(key)
  if agg is None:
    agg = make_variant("interaction_rule", name, values)
    variants[key] = agg
  else:
    merge_jinx_values(agg, values)
  add_common_source_data(agg, script, item)

  if name.startswith("unnamed jinx "):
    agg["issue_notes"].add("missing_jinx_name")
  if len(split_interaction_name(name)) < 2 and not (source_character and (target_name or target_id)):
    agg["issue_notes"].add("interaction_name_without_ampersand")
  if target_id and not target_name:
    agg["issue_notes"].add("nested_jinx_target_id_unresolved")


def add_nested_jinxes(
  variants: dict[Any, dict[str, Any]],
  script: ScriptData,
  item: dict[str, Any],
  global_ids: dict[str, set[str]],
) -> None:
  source_name = clean_text(item.get("name"))
  jinxes = item.get("jinxes")
  if not source_name or not isinstance(jinxes, list):
    return

  for jinx in jinxes:
    if not isinstance(jinx, dict):
      continue
    target_id = clean_text(jinx.get("id"))
    reason = clean_text(jinx.get("reason"))
    target_name = resolve_jinx_target_name(target_id, script, global_ids)
    display_target = target_name or target_id
    interaction_name = f"{source_name} & {display_target}" if display_target else source_name
    add_interaction(
      variants=variants,
      script=script,
      item=item,
      name=interaction_name,
      team="nested jinx",
      ability=reason,
      source_character=source_name,
      target_id=target_id,
      target_name=target_name,
    )


def collect_variants(scripts: list[ScriptData], global_ids: dict[str, set[str]]) -> dict[Any, dict[str, Any]]:
  variants: dict[Any, dict[str, Any]] = {}
  for script in scripts:
    for index, item in enumerate(script.entries):
      if not isinstance(item, dict) or is_meta_entry(item, index):
        continue

      team = clean_text(item.get("team"))
      name = clean_text(item.get("name"))
      ability = clean_text(item.get("ability"))
      if is_jinx_team(team):
        add_interaction(variants, script, item, name, "jinx", ability)
        continue

      add_character(variants, script, item)
      add_nested_jinxes(variants, script, item, global_ids)

  assign_variant_numbers(list(variants.values()))
  return variants


def assign_variant_numbers(aggs: list[dict[str, Any]]) -> None:
  groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
  for agg in aggs:
    groups[(agg["record_type"], agg["name"])].append(agg)

  for group in groups.values():
    group.sort(key=lambda agg: tuple(agg["values"].get(field, "") for field in VARIANT_VALUE_FIELDS))
    for index, agg in enumerate(group, start=1):
      agg["variant_index"] = index
      agg["variants_for_name"] = len(group)


def row_from_agg(agg: dict[str, Any], columns: list[str]) -> dict[str, str]:
  values = agg["values"]
  row = {column: "" for column in columns}
  row.update(values)
  row.update({
    "name": agg["name"],
    "variant_index": str(agg["variant_index"]),
    "variants_for_name": str(agg["variants_for_name"]),
    "occurrence_count": str(agg["occurrence_count"]),
    "raw_keys": joined(agg["raw_keys"]),
    "source_script_count": str(len(agg["source_scripts"])),
    "source_scripts": joined(agg["source_scripts"]),
    "source_author_count": str(len(agg["source_authors"])),
    "source_authors": joined(agg["source_authors"]),
    "source_file_count": str(len(agg["source_files"])),
    "source_files": joined(agg["source_files"]),
    "source_ids": joined(agg["source_ids"]),
    "issue_notes": joined(agg["issue_notes"]),
    "missing_first_night_reminder": "yes"
    if agg["missing_first_night_reminder_sources"]
    else "no",
    "missing_first_night_reminder_sources": joined(agg["missing_first_night_reminder_sources"]),
    "missing_other_night_reminder": "yes"
    if agg["missing_other_night_reminder_sources"]
    else "no",
    "missing_other_night_reminder_sources": joined(agg["missing_other_night_reminder_sources"]),
  })
  return row


def build_rows(
  variants: dict[Any, dict[str, Any]],
  record_type: str,
  columns: list[str],
) -> list[dict[str, str]]:
  aggs = sorted(
    [agg for agg in variants.values() if agg["record_type"] == record_type],
    key=lambda agg: (agg["record_type"], agg["name"], agg["variant_index"]),
  )
  return [row_from_agg(agg, columns) for agg in aggs]


def variant_label(agg: dict[str, Any]) -> str:
  if agg["variants_for_name"] == 1:
    return agg["name"]
  return f"{agg['name']}#variant-{agg['variant_index']}"


def issue_group_rows(issue_type: str, groups: dict[str, set[str]]) -> list[dict[str, str]]:
  rows = []
  for value, samples in sorted(groups.items()):
    rows.append({
      "issue_type": issue_type,
      "value": value,
      "count": str(len(samples)),
      "sample_names": value,
      "sample_files": JOINER.join(sorted(samples)[:20]),
      "details": "",
    })
  return rows


def issue_rows_from_variants(variants: dict[Any, dict[str, Any]]) -> list[dict[str, str]]:
  rows: list[dict[str, str]] = []
  unexpected_team_samples: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
  missing_first: dict[str, set[str]] = defaultdict(set)
  missing_other: dict[str, set[str]] = defaultdict(set)
  interaction_no_amp: dict[str, set[str]] = defaultdict(set)
  unresolved_nested: dict[str, set[str]] = defaultdict(set)

  for agg in variants.values():
    label = variant_label(agg)
    values = agg["values"]
    unexpected_team = values.get("unexpected_team", "")
    if unexpected_team:
      unexpected_team_samples[unexpected_team]["names"].add(agg["name"])
      unexpected_team_samples[unexpected_team]["files"].update(agg["source_files"])
    if agg["missing_first_night_reminder_sources"]:
      missing_first[label].update(agg["missing_first_night_reminder_sources"])
    if agg["missing_other_night_reminder_sources"]:
      missing_other[label].update(agg["missing_other_night_reminder_sources"])
    if "interaction_name_without_ampersand" in agg["issue_notes"]:
      interaction_no_amp[label].update(agg["source_files"])
    if "nested_jinx_target_id_unresolved" in agg["issue_notes"]:
      unresolved_nested[label].update(agg["source_files"])

  for team, samples in sorted(unexpected_team_samples.items()):
    rows.append({
      "issue_type": "unexpected_team_value",
      "value": team,
      "count": str(sum(1 for agg in variants.values() if agg["values"].get("unexpected_team") == team)),
      "sample_names": JOINER.join(sorted(samples["names"])[:20]),
      "sample_files": JOINER.join(sorted(samples["files"])[:20]),
      "details": "Team value is not one of the expected character teams and is not a jinx team.",
    })

  rows.extend(issue_group_rows("missing_first_night_reminder", missing_first))
  rows.extend(issue_group_rows("missing_other_night_reminder", missing_other))
  rows.extend(issue_group_rows("interaction_name_without_ampersand", interaction_no_amp))
  rows.extend(issue_group_rows("nested_jinx_target_id_unresolved", unresolved_nested))
  return rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Collect BOTC character variants and jinx interaction rules into separate CSV files."
  )
  parser.add_argument(
    "--input-dir",
    default=DEFAULT_INPUT_DIR,
    help=f"Directory containing JSON files. Default: {DEFAULT_INPUT_DIR}",
  )
  parser.add_argument(
    "--characters-output",
    default=DEFAULT_CHARACTERS_OUTPUT,
    help=f"Character CSV path. Default: {DEFAULT_CHARACTERS_OUTPUT}",
  )
  parser.add_argument(
    "--jinxes-output",
    default=DEFAULT_JINXES_OUTPUT,
    help=f"Jinx CSV path. Default: {DEFAULT_JINXES_OUTPUT}",
  )
  parser.add_argument(
    "--issues-output",
    default=DEFAULT_ISSUES_OUTPUT,
    help=f"Diagnostics CSV path. Default: {DEFAULT_ISSUES_OUTPUT}",
  )
  parser.add_argument(
    "--fetch-url-files",
    action="store_true",
    help="If a .json file contains only a URL, fetch and parse that URL.",
  )
  return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(sys.argv[1:] if argv is None else argv)
  input_dir = Path(args.input_dir)
  characters_output = Path(args.characters_output)
  jinxes_output = Path(args.jinxes_output)
  issues_output = Path(args.issues_output)

  scripts, load_issues = load_scripts(input_dir, args.fetch_url_files)
  global_ids = build_global_id_map(scripts)
  variants = collect_variants(scripts, global_ids)
  character_rows = build_rows(variants, "character", CHARACTER_COLUMNS)
  jinx_rows = build_rows(variants, "interaction_rule", JINX_COLUMNS)
  issue_rows = load_issues + issue_rows_from_variants(variants)

  write_csv(characters_output, CHARACTER_COLUMNS, character_rows)
  write_csv(jinxes_output, JINX_COLUMNS, jinx_rows)
  write_csv(issues_output, ISSUE_COLUMNS, issue_rows)

  record_counts = Counter(agg["record_type"] for agg in variants.values())
  unexpected_teams = Counter(
    agg["values"]["unexpected_team"]
    for agg in variants.values()
    if agg["values"].get("unexpected_team")
  )

  print(f"Wrote {characters_output} ({len(character_rows)} rows)")
  print(f"Wrote {jinxes_output} ({len(jinx_rows)} rows)")
  print(f"Wrote {issues_output} ({len(issue_rows)} rows)")
  print(f"Parsed {len(scripts)} JSON scripts")
  print(f"Character variants: {record_counts['character']}")
  print(f"Interaction rule variants: {record_counts['interaction_rule']}")
  if unexpected_teams:
    team_text = ", ".join(f"{team}={count}" for team, count in sorted(unexpected_teams.items()))
    print(f"Unexpected team values: {team_text}")
  else:
    print("Unexpected team values: none")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
