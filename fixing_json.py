#!/usr/bin/env python3
"""Small data fixups for the BOTC JSON collection."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_INPUT_DIR = "all_jsons"
TEAM_RE = re.compile(rb'("team"\s*:\s*")(?P<team>traveller2|traveller)(")')
JINX_TEAM_RE = re.compile(rb'("team"\s*:\s*")(?P<team>[^"]*jinx[^"]*)(")', re.IGNORECASE)
SETUP_RE = re.compile(
  rb'("setup"\s*:\s*)(?P<value>true|false|null|""|"true"|"false"|"null"|[2-9]\d*|1\d+)'
)


def clean_text(value: object) -> str:
  if value is None:
    return ""
  if isinstance(value, str):
    return re.sub(r"\s+", " ", value).strip()
  return str(value).strip()


def has_night_order(value: object) -> bool:
  try:
    return float(value or 0) != 0
  except (TypeError, ValueError):
    return False


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Apply safe, targeted fixes to BOTC JSON files.")
  parser.add_argument(
    "--input-dir",
    default=DEFAULT_INPUT_DIR,
    help=f"Directory containing JSON files. Default: {DEFAULT_INPUT_DIR}",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Report files that would change without writing them.",
  )
  return parser.parse_args()


def backfill_missing_reminders(data: object) -> Counter[str]:
  counts: Counter[str] = Counter()
  if not isinstance(data, list):
    return counts

  for item in data:
    if not isinstance(item, dict):
      continue
    ability = clean_text(item.get("ability"))
    if not ability:
      continue

    first_reminder = item.get("firstNightReminder", item.get("firstReminder", ""))
    if has_night_order(item.get("firstNight")) and not clean_text(first_reminder):
      item["firstNightReminder"] = ability
      counts["firstNightReminder:ability"] += 1

    other_reminder = item.get("otherNightReminder", item.get("ogherNightReminder", ""))
    if has_night_order(item.get("otherNight")) and not clean_text(other_reminder):
      item["otherNightReminder"] = ability
      counts["otherNightReminder:ability"] += 1

  return counts


def fix_file(path: Path, dry_run: bool) -> Counter[str]:
  original = path.read_bytes()
  counts: Counter[str] = Counter()

  def replace_team(match: re.Match[bytes]) -> bytes:
    team = match.group("team").decode("ascii")
    counts[team] += 1
    return match.group(1) + b"traveler" + match.group(3)

  def replace_jinx_team(match: re.Match[bytes]) -> bytes:
    team = match.group("team").decode("utf-8")
    if team == "jinx":
      return match.group(0)
    counts[f"jinx_team:{team}->jinx"] += 1
    return match.group(1) + b"jinx" + match.group(3)

  def replace_setup(match: re.Match[bytes]) -> bytes:
    value = match.group("value").decode("ascii")
    if value in ("true", '"true"') or value.isdigit():
      counts[f"setup:{value}->1"] += 1
      return match.group(1) + b"1"
    counts[f"setup:{value}->0"] += 1
    return match.group(1) + b"0"

  fixed = TEAM_RE.sub(replace_team, original)
  fixed = JINX_TEAM_RE.sub(replace_jinx_team, fixed)
  fixed = SETUP_RE.sub(replace_setup, fixed)

  try:
    parsed = json.loads(fixed.decode("utf-8-sig"))
  except (UnicodeDecodeError, json.JSONDecodeError):
    parsed = None

  if parsed is not None:
    reminder_counts = backfill_missing_reminders(parsed)
    if reminder_counts:
      counts.update(reminder_counts)
      fixed = (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

  if fixed != original and not dry_run:
    path.write_bytes(fixed)
  return counts


def main() -> int:
  args = parse_args()
  input_dir = Path(args.input_dir)
  total_counts: Counter[str] = Counter()
  changed_files = 0

  for path in sorted(input_dir.rglob("*.json")):
    counts = fix_file(path, args.dry_run)
    if counts:
      changed_files += 1
      total_counts.update(counts)
      details = ", ".join(f"{team}={count}" for team, count in sorted(counts.items()))
      action = "would fix" if args.dry_run else "fixed"
      print(f"{action}: {path} ({details})")

  action = "Would update" if args.dry_run else "Updated"
  total_details = ", ".join(f"{team}={count}" for team, count in sorted(total_counts.items()))
  print(f"{action} {changed_files} files")
  print(f"Replacement counts: {total_details or 'none'}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
