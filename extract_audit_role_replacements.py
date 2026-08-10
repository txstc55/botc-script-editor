#!/usr/bin/env python3
"""Find unambiguous same-team role replacements from the board audit."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from audit_bilibili_scripts import (
  build_ocr_tool,
  clean_space,
  ngram_coverage,
  ocr_lines,
)


ROOT = Path("bilibili_script_audit")
TEAM_DIRS = {
  "townsfolks": "townsfolk",
  "outsiders": "outsider",
  "minions": "minion",
  "demons": "demon",
  "travelers": "traveler",
  "fabled": "fabled",
}


def team_by_name() -> dict[str, set[str]]:
  result: dict[str, set[str]] = defaultdict(set)
  root = Path("script_editor/public/characters")
  for directory, team in TEAM_DIRS.items():
    path = root / directory / "index.json"
    if not path.exists():
      continue
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data.get("characters", []):
      if isinstance(item, dict):
        result[clean_space(item.get("name"))].add(team)
  return result


def character_rows() -> dict[tuple[str, str], list[dict[str, str]]]:
  result: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
  with Path("botc_characters.csv").open(encoding="utf-8-sig", newline="") as handle:
    for row in csv.DictReader(handle):
      result[(clean_space(row.get("name")), clean_space(row.get("normalized_team")))].append(row)
  return result


def number(value: str) -> int | float:
  parsed = float(value or 0)
  return int(parsed) if parsed.is_integer() else parsed


def values(value: str) -> list[str]:
  return [item.strip() for item in str(value or "").split("||") if item.strip()]


def row_entry(row: dict[str, str]) -> dict[str, Any]:
  name = clean_space(row.get("name"))
  return {
    "id": name,
    "name": name,
    "team": clean_space(row.get("normalized_team")),
    "ability": clean_space(row.get("ability")),
    "image": clean_space(row.get("image")),
    "firstNight": number(row.get("first_night_order", "0")),
    "firstNightReminder": clean_space(row.get("first_night_reminder")),
    "otherNight": number(row.get("other_night_order", "0")),
    "otherNightReminder": clean_space(row.get("other_night_reminder")),
    "reminders": values(row.get("reminders", "")),
    "remindersGlobal": values(row.get("reminders_global", "")),
    "setup": int(number(row.get("setup", "0")) != 0),
    "flavor": clean_space(row.get("flavor")),
  }


def main() -> None:
  summary = json.loads((ROOT / "核对汇总.json").read_text(encoding="utf-8"))
  known_teams = team_by_name()
  rows = character_rows()
  ocr_binary = build_ocr_tool(ROOT)
  candidates: list[dict[str, Any]] = []
  for item in summary.get("items", []):
    missing = [clean_space(value) for value in item.get("missing_characters", [])]
    unexpected = [clean_space(value) for value in item.get("unexpected_characters", [])]
    if not missing or not unexpected:
      continue
    folder = Path(item["folder"])
    metadata = json.loads((folder / "核对状态.json").read_text(encoding="utf-8"))
    local_json_value = clean_space(metadata.get("local_json"))
    local_json = Path(local_json_value)
    image_name = clean_space(metadata.get("ocr_reference_image"))
    if not local_json_value or not local_json.is_file() or not image_name:
      continue
    data = json.loads(local_json.read_text(encoding="utf-8"))
    local_teams = {
      clean_space(entry.get("name")): clean_space(entry.get("team"))
      for entry in data if isinstance(entry, dict)
    }
    missing_by_team: dict[str, list[str]] = defaultdict(list)
    unexpected_by_team: dict[str, list[str]] = defaultdict(list)
    for name in missing:
      missing_by_team[local_teams.get(name, "")].append(name)
    for name in unexpected:
      teams = known_teams.get(name, set())
      if len(teams) == 1:
        unexpected_by_team[next(iter(teams))].append(name)
    simple_pairs = [
      (team, old_names[0], unexpected_by_team[team][0])
      for team, old_names in missing_by_team.items()
      if len(old_names) == 1 and len(unexpected_by_team.get(team, [])) == 1
    ]
    if not simple_pairs:
      continue
    board_text = "\n".join(
      clean_space(line.get("text"))
      for line in ocr_lines(ocr_binary, folder / image_name)
    )
    for team, old_name, new_name in simple_pairs:
      variants = rows.get((new_name, team), [])
      scored = sorted([
        (
          ngram_coverage(row.get("ability", ""), board_text),
          int(row.get("occurrence_count", 0) or 0),
          row,
        )
        for row in variants
      ], key=lambda value: (value[0], value[1]), reverse=True)
      if not scored:
        continue
      score, occurrence_count, row = scored[0]
      candidates.append({
        "script_name": item["script_name"],
        "opus_id": item["opus_id"],
        "local_json": str(local_json),
        "reference_image": str(folder / image_name),
        "team": team,
        "old_name": old_name,
        "new_name": new_name,
        "ability_coverage": round(score, 4),
        "occurrence_count": occurrence_count,
        "entry": row_entry(row),
      })

  output = ROOT / "角色替换候选.json"
  output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  print(f"角色替换候选 {len(candidates)} 条，能力高置信度 {sum(item['ability_coverage'] >= 0.65 for item in candidates)} 条。")
  print(output)


if __name__ == "__main__":
  main()
