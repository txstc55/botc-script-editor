#!/usr/bin/env python3
"""Apply targeted character fixes to the BOTC JSON collection."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = "all_jsons"
TEAM_ALIASES = {
  "minion": "minion",
  "minions": "minion",
  "爪牙": "minion",
}
NIGHT_ORDER_KEYS = ("firstNight", "otherNight")


def clean_text(value: Any) -> str:
  if value is None:
    return ""
  if isinstance(value, str):
    return re.sub(r"\s+", " ", value).strip()
  return str(value).strip()


def normalized_team(value: Any) -> str:
  return TEAM_ALIASES.get(clean_text(value).lower(), clean_text(value))


def json_paths(input_dir: Path) -> list[Path]:
  return sorted(
    path
    for path in input_dir.rglob("*")
    if path.is_file() and path.suffix.lower() == ".json"
  )


class CharacterFix:
  def __init__(self, name: str, teams: set[str], updates: dict[str, Any]) -> None:
    self.name = name
    self.teams = teams
    self.updates = updates

  def matches(self, item: dict[str, Any]) -> bool:
    return clean_text(item.get("name")) == self.name and normalized_team(item.get("team")) in self.teams

  def apply(self, item: dict[str, Any]) -> bool:
    if not self.matches(item):
      return False

    original_night_orders = {
      key: item[key]
      for key in NIGHT_ORDER_KEYS
      if key in item
    }
    changed = False
    for key, value in self.updates.items():
      if key in NIGHT_ORDER_KEYS:
        continue
      if item.get(key) != value:
        item[key] = value
        changed = True

    for key, value in original_night_orders.items():
      item[key] = value

    return changed


class CharacterFixRunner:
  def __init__(self, fixes: list[CharacterFix]) -> None:
    self.fixes = fixes

  def apply_to_data(self, data: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in self.iter_character_items(data):
      for fix in self.fixes:
        if fix.apply(item):
          counts[fix.name] += 1
    return counts

  def iter_character_items(self, data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
      return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
      items: list[dict[str, Any]] = []
      for key in ("characters", "roles", "script", "items", "data"):
        value = data.get(key)
        if isinstance(value, list):
          items.extend(item for item in value if isinstance(item, dict))
      if not items:
        items.append(data)
      return items
    return []

  def apply_to_file(self, path: Path, dry_run: bool) -> Counter[str]:
    original = path.read_text(encoding="utf-8-sig")
    data = json.loads(original)
    counts = self.apply_to_data(data)
    if counts and not dry_run:
      path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts


CHARACTER_FIXES = [
  CharacterFix(
    name="教父",
    teams={"minion"},
    updates={
      "ability": "在你的首个夜晚，你会得知有哪些外来者角色在场。如果有外来者在白天死亡，你会在当晚被唤醒并且你要选择一名玩家：他死亡。[-1或+1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/godfather.png",
      "firstNightReminder": "唤醒教父，对他展示外来者角色标记，告诉他有哪些外来者在场。",
      "otherNightReminder": "如果今天白天有外来者死亡，唤醒教父，让他攻击一名玩家。",
      "reminders": [
        "死于今日",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "通常来说，这只是件小事。但在你侮辱我女儿时，你就侮辱了我。你侮辱我，就侮辱了我的家族。你真的应该更小心些——要是你不幸发生意外事故，那就太遗憾了。",
    },
  ),
]


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Apply specific character fixes to BOTC JSON files.")
  parser.add_argument(
    "--input-dir",
    default=DEFAULT_INPUT_DIR,
    help=f"Directory containing JSON files. Default: {DEFAULT_INPUT_DIR}",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Report fixes without writing files.",
  )
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  runner = CharacterFixRunner(CHARACTER_FIXES)
  input_dir = Path(args.input_dir)
  total_counts: Counter[str] = Counter()
  changed_files = 0
  failed_files: list[tuple[Path, str]] = []

  for path in json_paths(input_dir):
    try:
      counts = runner.apply_to_file(path, args.dry_run)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
      failed_files.append((path, str(exc)))
      continue
    if counts:
      changed_files += 1
      total_counts.update(counts)

  action = "Would update" if args.dry_run else "Updated"
  print(f"{action} {changed_files} files")
  for name, count in sorted(total_counts.items()):
    print(f"{name}: {count} character entries")
  if failed_files:
    print(f"Skipped {len(failed_files)} unreadable JSON files")
    for path, error in failed_files[:20]:
      print(f"- {path}: {error}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
