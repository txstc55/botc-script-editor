#!/usr/bin/env python3
"""Generate static app database JSON files from extracted BOTC CSVs."""

from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CHARACTER_CSV = ROOT / "botc_characters.csv"
JINX_CSV = ROOT / "botc_jinxes.csv"
PUBLIC_ROOT = ROOT / "script_editor" / "public"
CHARACTER_ROOT = PUBLIC_ROOT / "characters"
JINX_ROOT = PUBLIC_ROOT / "jinxes"
ISSUE_OUTPUT = PUBLIC_ROOT / "database_generation_issues.json"

TEAM_FOLDERS = {
  "townsfolk": "townsfolks",
  "outsider": "outsiders",
  "minion": "minions",
  "demon": "demons",
  "traveler": "travelers",
  "fabled": "fabled",
}

TEAM_LABELS_ZH = {
  "townsfolk": "镇民",
  "outsider": "外来者",
  "minion": "爪牙",
  "demon": "恶魔",
  "traveler": "旅行者",
  "fabled": "传奇角色",
}

RESERVED_FILENAME_CHARS = str.maketrans(
  {
    "/": "／",
    "\\": "＼",
    ":": "：",
    "*": "＊",
    "?": "？",
    '"': "＂",
    "<": "＜",
    ">": "＞",
    "|": "｜",
  }
)
CONTROL_FILENAME_CHARS = re.compile(r"[\x00-\x1f]")


def text(value: Any) -> str:
  return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
  if not path.exists():
    raise FileNotFoundError(path)
  with path.open(newline="", encoding="utf-8-sig") as handle:
    return list(csv.DictReader(handle))


def split_list(value: str) -> list[str]:
  parts = [part.strip() for part in text(value).split("||")]
  return dedupe([part for part in parts if part])


def split_notes(value: str) -> list[str]:
  raw = text(value)
  if not raw:
    return []
  if "||" in raw:
    return split_list(raw)
  return [raw]


def dedupe(values: list[str]) -> list[str]:
  seen: set[str] = set()
  result: list[str] = []
  for value in values:
    cleaned = text(value)
    if cleaned and cleaned not in seen:
      seen.add(cleaned)
      result.append(cleaned)
  return result


def parse_int(value: Any, default: int = 0) -> int:
  raw = text(value)
  if not raw:
    return default
  try:
    return int(float(raw))
  except ValueError:
    return default


def parse_setup(value: Any) -> int:
  raw = text(value).lower()
  if raw in {"", "0", "false", "no", "none", "null"}:
    return 0
  if raw in {"1", "true", "yes"}:
    return 1
  return 1 if parse_int(raw, 0) else 0


def file_stem(name: str, fallback: str) -> str:
  normalized = unicodedata.normalize("NFKC", text(name))
  cleaned = normalized.translate(RESERVED_FILENAME_CHARS)
  cleaned = CONTROL_FILENAME_CHARS.sub("_", cleaned)
  cleaned = re.sub(r"\s+", "_", cleaned).strip(" .")
  if not cleaned:
    cleaned = fallback
  return cleaned[:120]


def unique_filename(name: str, fallback: str, used: dict[str, str]) -> tuple[str, dict[str, Any] | None]:
  stem = file_stem(name, fallback)
  filename = f"{stem}.json"
  if filename not in used or used[filename] == name:
    used[filename] = name
    return filename, None

  suffix = 2
  while True:
    candidate = f"{stem}--{suffix}.json"
    if candidate not in used:
      used[candidate] = name
      return candidate, {
        "type": "filename_collision",
        "name": name,
        "conflictingName": used[filename],
        "baseFilename": filename,
        "filename": candidate,
      }
    suffix += 1


def write_json(path: Path, payload: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")


def reset_dir(path: Path) -> None:
  if path.exists():
    shutil.rmtree(path)
  path.mkdir(parents=True, exist_ok=True)


def source_payload(row: dict[str, str]) -> dict[str, Any]:
  return {
    "scriptCount": parse_int(row.get("source_script_count")),
    "scripts": split_list(row.get("source_scripts", "")),
    "authorCount": parse_int(row.get("source_author_count")),
    "authors": split_list(row.get("source_authors", "")),
    "fileCount": parse_int(row.get("source_file_count")),
    "files": split_list(row.get("source_files", "")),
    "ids": split_list(row.get("source_ids", "")),
  }


def character_notes(row: dict[str, str]) -> list[str]:
  notes = split_notes(row.get("issue_notes", ""))
  if text(row.get("missing_first_night_reminder")) == "yes":
    notes.append("missing_first_night_reminder")
  if text(row.get("missing_other_night_reminder")) == "yes":
    notes.append("missing_other_night_reminder")
  return dedupe(notes)


def canonical_variant_key(value: Any) -> str:
  return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_trait_variants(
  rows: list[dict[str, str]],
  readers: dict[str, Any],
) -> dict[str, list[Any]]:
  variants: dict[str, list[Any]] = {}

  for trait, reader in readers.items():
    counter: Counter[str] = Counter()
    values: dict[str, Any] = {}
    for row in rows:
      value = reader(row)
      key = canonical_variant_key(value)
      values[key] = value
      counter[key] += parse_int(row.get("occurrence_count"), 1)

    ordered_keys = sorted(counter, key=lambda key: (-counter[key], key))
    variants[trait] = [values[key] for key in ordered_keys]

  return variants


CHARACTER_TRAIT_READERS = {
  "ability": lambda row: text(row.get("ability")),
  "image": lambda row: text(row.get("image")),
  "firstNight": lambda row: parse_int(row.get("first_night_order")),
  "firstNightReminder": lambda row: text(row.get("first_night_reminder")),
  "otherNight": lambda row: parse_int(row.get("other_night_order")),
  "otherNightReminder": lambda row: text(row.get("other_night_reminder")),
  "reminders": lambda row: split_list(row.get("reminders", "")),
  "remindersGlobal": lambda row: split_list(row.get("reminders_global", "")),
  "setup": lambda row: parse_setup(row.get("setup")),
  "flavor": lambda row: text(row.get("flavor")),
}


def build_characters(rows: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
  grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
  issues: list[dict[str, Any]] = []

  for row_number, row in enumerate(rows, 2):
    name = text(row.get("name"))
    team = text(row.get("normalized_team")) or text(row.get("team"))
    if not name:
      issues.append({"type": "character_missing_name", "row": row_number})
      continue
    if team not in TEAM_FOLDERS:
      issues.append(
        {
          "type": "character_unexpected_team",
          "row": row_number,
          "name": name,
          "team": text(row.get("team")),
          "normalizedTeam": text(row.get("normalized_team")),
          "occurrenceCount": parse_int(row.get("occurrence_count"), 1),
        }
      )
      continue
    grouped[(team, name)].append(row)

  team_entries: dict[str, list[dict[str, Any]]] = {team: [] for team in TEAM_FOLDERS}
  used_filenames: dict[str, dict[str, str]] = {
    folder: {}
    for folder in TEAM_FOLDERS.values()
  }
  total_occurrences = 0

  for team in TEAM_FOLDERS:
    (CHARACTER_ROOT / TEAM_FOLDERS[team]).mkdir(parents=True, exist_ok=True)

  for (team, name), group_rows in grouped.items():
    variants = build_trait_variants(group_rows, CHARACTER_TRAIT_READERS)
    occurrence_count = sum(parse_int(row.get("occurrence_count"), 1) for row in group_rows)
    notes = dedupe([
      note
      for row in group_rows
      for note in character_notes(row)
    ])
    total_occurrences += occurrence_count

    folder = TEAM_FOLDERS[team]
    filename, filename_issue = unique_filename(name, "character", used_filenames[folder])
    if filename_issue:
      issues.append({"folder": folder, **filename_issue})
    payload = {
      "id": name,
      "name": name,
      "team": team,
      "totalOccurrenceCount": occurrence_count,
      "notes": notes,
      "variants": variants,
    }
    write_json(CHARACTER_ROOT / folder / filename, payload)
    team_entries[team].append(
      {
        "id": name,
        "name": name,
        "team": team,
        "totalOccurrenceCount": occurrence_count,
      }
    )

  team_index_payloads: list[dict[str, Any]] = []
  for team, entries in team_entries.items():
    entries.sort(key=lambda item: (-item["totalOccurrenceCount"], item["name"]))
    payload = {
      "team": team,
      "folder": TEAM_FOLDERS[team],
      "characterCount": len(entries),
      "totalOccurrenceCount": sum(item["totalOccurrenceCount"] for item in entries),
      "characters": entries,
    }
    write_json(CHARACTER_ROOT / TEAM_FOLDERS[team] / "index.json", payload)
    team_index_payloads.append(payload)

  index_payload = {
    "source": str(CHARACTER_CSV.relative_to(ROOT)),
    "characterCount": sum(len(entries) for entries in team_entries.values()),
    "totalOccurrenceCount": total_occurrences,
    "teams": [
      {
        "team": payload["team"],
        "folder": payload["folder"],
        "indexPath": f"/characters/{payload['folder']}/index.json",
        "characterCount": payload["characterCount"],
        "totalOccurrenceCount": payload["totalOccurrenceCount"],
      }
      for payload in team_index_payloads
    ],
  }
  write_json(CHARACTER_ROOT / "index.json", index_payload)
  return index_payload, issues


def ampersand_targets(name: str) -> list[str]:
  if "&" not in name:
    return []
  return dedupe([part.strip() for part in re.split(r"\s*&\s*", name) if part.strip()])


def normalize_name_target(target: str, detected_targets: list[str]) -> str:
  cleaned = text(target)
  if not cleaned or cleaned in detected_targets:
    return cleaned

  parts = [part.strip() for part in cleaned.split("：") if part.strip()]
  for index in range(1, len(parts)):
    suffix = "：".join(parts[index:])
    if suffix in detected_targets:
      return suffix
  return cleaned


def jinx_targets(row: dict[str, str]) -> list[str]:
  detected_targets = split_list(row.get("jinx_targets", ""))
  name_targets = [
    normalize_name_target(target, detected_targets)
    for target in ampersand_targets(text(row.get("name")))
  ]
  targets = name_targets + detected_targets
  source_team = text(row.get("team"))
  source_character = text(row.get("rule_source_character"))
  target_name = text(row.get("rule_target_name")) or text(row.get("rule_target_id"))

  if source_team == "nested jinx":
    targets.extend([source_character, target_name])

  if not targets:
    targets.extend(ampersand_targets(text(row.get("name"))))

  return dedupe(targets)


JINX_TRAIT_READERS = {
  "ability": lambda row: text(row.get("ability")),
}


def build_jinxes(rows: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
  grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
  issues: list[dict[str, Any]] = []

  for row_number, row in enumerate(rows, 2):
    name = text(row.get("name"))
    if not name:
      issues.append({"type": "jinx_missing_name", "row": row_number})
      continue
    grouped[name].append(row)

  entries: list[dict[str, Any]] = []
  used_filenames: dict[str, str] = {}
  total_occurrences = 0

  for name, group_rows in grouped.items():
    variants = build_trait_variants(group_rows, JINX_TRAIT_READERS)
    occurrence_count = sum(parse_int(row.get("occurrence_count"), 1) for row in group_rows)
    targets = dedupe([
      target
      for row in group_rows
      for target in jinx_targets(row)
    ])
    target_detection_notes = dedupe([
      note
      for row in group_rows
      for note in split_notes(row.get("target_detection_notes", ""))
    ])
    issue_notes = dedupe([
      note
      for row in group_rows
      for note in split_notes(row.get("issue_notes", ""))
    ])
    total_occurrences += occurrence_count

    filename, filename_issue = unique_filename(name, "jinx", used_filenames)
    if filename_issue:
      issues.append({"folder": "jinxes", **filename_issue})
    payload = {
      "id": name,
      "name": name,
      "team": "jinx",
      "targets": targets,
      "targetDetectionNotes": target_detection_notes,
      "issueNotes": issue_notes,
      "totalOccurrenceCount": occurrence_count,
      "variants": variants,
    }
    write_json(JINX_ROOT / filename, payload)
    entries.append(
      {
        "id": name,
        "name": name,
        "team": "jinx",
        "totalOccurrenceCount": occurrence_count,
      }
    )

  entries.sort(key=lambda item: (-item["totalOccurrenceCount"], item["name"]))
  index_payload = {
    "source": str(JINX_CSV.relative_to(ROOT)),
    "jinxCount": len(entries),
    "totalOccurrenceCount": total_occurrences,
    "jinxes": entries,
  }
  write_json(JINX_ROOT / "index.json", index_payload)
  return index_payload, issues


def issue_summary(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
  counter = Counter(
    (
      issue["type"],
      issue.get("team") or issue.get("normalizedTeam") or "",
    )
    for issue in issues
  )
  return [
    {"type": issue_type, "value": value, "count": count}
    for (issue_type, value), count in sorted(counter.items())
  ]


def main() -> None:
  character_rows = read_csv(CHARACTER_CSV)
  jinx_rows = read_csv(JINX_CSV)

  reset_dir(CHARACTER_ROOT)
  reset_dir(JINX_ROOT)

  character_index, character_issues = build_characters(character_rows)
  jinx_index, jinx_issues = build_jinxes(jinx_rows)
  issues = character_issues + jinx_issues

  manifest = {
    "characters": {
      "indexPath": "/characters/index.json",
      "characterCount": character_index["characterCount"],
      "totalOccurrenceCount": character_index["totalOccurrenceCount"],
    },
    "jinxes": {
      "indexPath": "/jinxes/index.json",
      "jinxCount": jinx_index["jinxCount"],
      "totalOccurrenceCount": jinx_index["totalOccurrenceCount"],
    },
    "issuesPath": "/database_generation_issues.json",
  }
  write_json(PUBLIC_ROOT / "database_manifest.json", manifest)
  write_json(
    ISSUE_OUTPUT,
    {
      "issueCount": len(issues),
      "summary": issue_summary(issues),
      "issues": issues,
    },
  )

  print(
    "Generated "
    f"{character_index['characterCount']} character files, "
    f"{jinx_index['jinxCount']} jinx files."
  )
  if issues:
    print(f"Recorded {len(issues)} generation issues in {ISSUE_OUTPUT.relative_to(ROOT)}.")


if __name__ == "__main__":
  main()
