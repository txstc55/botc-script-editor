#!/usr/bin/env python3
"""Small data fixups for the BOTC JSON collection."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = "all_jsons"
TEAM_RE = re.compile(rb'("team"\s*:\s*")(?P<team>traveller2|traveller)(")')
JINX_TEAM_RE = re.compile(rb'("team"\s*:\s*")(?P<team>[^"]*jinx[^"]*)(")', re.IGNORECASE)
SETUP_RE = re.compile(
  rb'("setup"\s*:\s*)(?P<value>true|false|null|""|"true"|"false"|"null"|[2-9]\d*|1\d+)'
)
URL_POINTER_RE = re.compile(r"^https?://\S+\.json(?:\?\S*)?$", re.IGNORECASE)
SCALAR_STRING_KEYS = {
  "ability",
  "almanac",
  "attribution",
  "flavor",
  "firstNightReminder",
  "firstReminder",
  "icon",
  "image",
  "logo",
  "ogherNightReminder",
  "otherNightReminder",
  "reason",
  "rule",
  "skill",
  "targetName",
}
QUOTE_WRAPPED_TEXT_KEYS = {
  "ability",
  "almanac",
  "attribution",
  "flavor",
  "firstNightReminder",
  "firstReminder",
  "icon",
  "image",
  "logo",
  "ogherNightReminder",
  "otherNightReminder",
  "reason",
  "rule",
  "skill",
  "targetName",
}
BRACKET_WRAPPED_TEXT_KEYS = {
  "almanac",
  "attribution",
  "firstNightReminder",
  "firstReminder",
  "flavor",
  "icon",
  "image",
  "logo",
  "ogherNightReminder",
  "otherNightReminder",
  "reason",
  "rule",
  "skill",
  "targetName",
}
CHARACTER_TEAMS = {"townsfolk", "outsider", "minion", "demon", "traveler", "fabled"}
CHARACTER_FIELDS = (
  "ability",
  "image",
  "firstNight",
  "firstNightReminder",
  "otherNight",
  "otherNightReminder",
  "reminders",
  "remindersGlobal",
  "setup",
  "flavor",
)
CHARACTER_DEFAULTS: dict[str, Any] = {
  "ability": "",
  "image": "",
  "firstNight": 0,
  "firstNightReminder": "",
  "otherNight": 0,
  "otherNightReminder": "",
  "reminders": [],
  "remindersGlobal": [],
  "setup": 0,
  "flavor": "",
}
CHARACTER_ID_OVERRIDES = {
  "bootlegger": ("私货商人", "fabled"),
  "gardener": ("园丁", "fabled"),
  "hermit": ("隐修者", "outsider"),
  "lilmonsta": ("小怪宝", "demon"),
  "witch": ("女巫", "minion"),
  "wraith": ("亡魂", "minion"),
}
CHARACTER_REFERENCE_OVERRIDES = {
  "hermit": Path("all_jsons/BWG·剧本大乱斗/BWG剧本大乱斗收录合集/#言出法随-讷之/#言出法随-讷之.json"),
  "wraith": Path("all_jsons/万象星启体验剧本/剧本/768#血肉磨坊-qqwawawawa.json"),
}
VIEW_ONLY_FIELDS = {"notes", "abilityHtml", "textHtml", "previewSection", "previewSectionLabel"}


def json_paths(input_dir: Path, file_name: str = "") -> list[Path]:
  return sorted(
    path
    for path in input_dir.rglob("*")
    if path.is_file() and path.suffix.lower() == ".json" and (not file_name or path.name == file_name)
  )


def normalized_character_id(value: object) -> str:
  return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def normalized_character_team(value: object) -> str:
  team = clean_text(value).lower()
  return "traveler" if team in {"traveller", "traveller2"} else team


def character_payload(item: dict[str, Any], character_id: str) -> dict[str, Any]:
  result: dict[str, Any] = {
    "id": character_id,
    "name": clean_text(item.get("name")),
    "team": normalized_character_team(item.get("team")),
  }
  for field in CHARACTER_FIELDS:
    result[field] = item.get(field, CHARACTER_DEFAULTS[field])
  setup = result["setup"]
  try:
    result["setup"] = int(float(setup or 0) != 0)
  except (TypeError, ValueError):
    result["setup"] = int(str(setup).strip().lower() == "true")
  return result


def build_character_id_registry(paths: list[Path]) -> tuple[dict[str, dict[str, Any]], set[str]]:
  needed_ids: set[str] = set()
  all_characters: list[dict[str, Any]] = []
  candidates_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
  reference_candidates: dict[str, dict[str, Any]] = {}
  for path in paths:
    try:
      data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
      continue
    if not isinstance(data, list):
      continue
    needed_ids.update(normalized_character_id(item) for item in data if isinstance(item, str))
    for item in data:
      if not isinstance(item, dict):
        continue
      name = clean_text(item.get("name"))
      team = normalized_character_team(item.get("team"))
      if not name or team not in CHARACTER_TEAMS:
        continue
      all_characters.append(item)
      for character_id, reference_path in CHARACTER_REFERENCE_OVERRIDES.items():
        if path == reference_path and (name, team) == CHARACTER_ID_OVERRIDES[character_id]:
          reference_candidates[character_id] = item
      for field in ("id", "name_id", "name_eng"):
        candidate_id = normalized_character_id(item.get(field))
        if candidate_id:
          candidates_by_id[candidate_id].append(item)

  registry: dict[str, dict[str, Any]] = {}
  unresolved: set[str] = set()
  for character_id in needed_ids:
    if character_id in reference_candidates:
      registry[character_id] = character_payload(reference_candidates[character_id], character_id)
      continue
    override = CHARACTER_ID_OVERRIDES.get(character_id)
    candidates = candidates_by_id.get(character_id, [])
    if override:
      candidates = [
        item for item in all_characters
        if (clean_text(item.get("name")), normalized_character_team(item.get("team"))) == override
      ]
    if not candidates:
      unresolved.add(character_id)
      continue
    identity_counts = Counter(
      (clean_text(item.get("name")), normalized_character_team(item.get("team")))
      for item in candidates
    )
    identity = override or identity_counts.most_common(1)[0][0]
    payload_counts: Counter[str] = Counter()
    for item in candidates:
      if (clean_text(item.get("name")), normalized_character_team(item.get("team"))) != identity:
        continue
      payload = character_payload(item, character_id)
      payload_counts[json.dumps(payload, ensure_ascii=False, sort_keys=True)] += 1
    if not payload_counts:
      unresolved.add(character_id)
      continue
    selected = max(
      payload_counts,
      key=lambda value: (
        payload_counts[value],
        len(clean_text(json.loads(value).get("ability"))),
      ),
    )
    registry[character_id] = json.loads(selected)
  return registry, unresolved


def expand_character_ids(data: object, registry: dict[str, dict[str, Any]]) -> Counter[str]:
  counts: Counter[str] = Counter()
  if not isinstance(data, list):
    return counts
  existing_identities = {
    (clean_text(item.get("name")), normalized_character_team(item.get("team")))
    for item in data if isinstance(item, dict)
  }
  expanded: list[object] = []
  for item in data:
    if not isinstance(item, str):
      expanded.append(item)
      continue
    character_id = normalized_character_id(item)
    character = registry.get(character_id)
    if not character:
      expanded.append(item)
      continue
    identity = (character["name"], character["team"])
    if identity in existing_identities:
      counts[f"duplicate_character_id:{item}"] += 1
      continue
    expanded.append(dict(character))
    existing_identities.add(identity)
    counts[f"character_id:{item}->{character['name']}"] += 1
  data[:] = expanded
  return counts


def clean_text(value: object) -> str:
  if value is None:
    return ""
  if isinstance(value, str):
    return re.sub(r"\s+", " ", value).strip()
  return str(value).strip()


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


def strip_view_only_fields(raw: bytes) -> tuple[bytes, Counter[str]]:
  has_bom = raw.startswith(b"\xef\xbb\xbf")
  text = raw.decode("utf-8-sig")
  counts: Counter[str] = Counter()
  for start, end in reversed(top_level_object_spans(text)):
    value = json.loads(text[start:end])
    if not isinstance(value, dict):
      continue
    removed = [field for field in VIEW_ONLY_FIELDS if field in value]
    if not removed:
      continue
    for field in removed:
      value.pop(field)
      counts[f"view_field:{field}"] += 1
    line_start = text.rfind("\n", 0, start) + 1
    base_indent = re.match(r"[ \t]*", text[line_start:start]).group(0)
    lines = json.dumps(value, ensure_ascii=False, indent=2).splitlines()
    replacement = lines[0] + "\n" + "\n".join(base_indent + line for line in lines[1:])
    text = text[:start] + replacement + text[end:]
  encoded = text.encode("utf-8")
  return (b"\xef\xbb\xbf" + encoded if has_bom else encoded), counts


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
  parser.add_argument("--file-name", default="", help="Only process JSON files with this exact name.")
  parser.add_argument("--view-only", action="store_true", help="Only remove editor-only display fields.")
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


def normalize_wrapped_text_values(data: object) -> Counter[str]:
  counts: Counter[str] = Counter()

  def visit(value: object, key: str) -> object:
    if isinstance(value, dict):
      for child_key, child_value in list(value.items()):
        value[child_key] = visit(child_value, str(child_key))
      return value

    if isinstance(value, list):
      if key == "image":
        image = first_clean_string(value)
        if image is not None:
          counts[f"scalar_array:{key}"] += 1
          return clean_wrapped_text(image, key, counts)
      if key in SCALAR_STRING_KEYS and len(value) == 1 and isinstance(value[0], str):
        counts[f"scalar_array:{key}"] += 1
        return clean_wrapped_text(value[0], key, counts)
      return [visit(item, key) for item in value]

    if isinstance(value, str):
      return clean_wrapped_text(value, key, counts)

    return value

  visit(data, "")
  return counts


def clean_wrapped_text(value: str, key: str, counts: Counter[str]) -> str:
  original = value
  cleaned = value.strip()

  changed = True
  while changed and len(cleaned) >= 2:
    changed = False
    if key in QUOTE_WRAPPED_TEXT_KEYS and is_wrapped_quote(cleaned):
      cleaned = cleaned[1:-1].strip()
      counts[f"wrapped_quote:{key or 'unknown'}"] += 1
      changed = True
      continue
    if key in BRACKET_WRAPPED_TEXT_KEYS and is_single_square_wrapper(cleaned):
      cleaned = cleaned[1:-1].strip()
      counts[f"wrapped_bracket:{key}"] += 1
      changed = True

  return cleaned if cleaned != original else value


def first_clean_string(values: list[object]) -> str | None:
  for value in values:
    if isinstance(value, str) and value.strip():
      return value
  return None


def is_wrapped_quote(value: str) -> bool:
  return (
    len(value) >= 2
    and value[0] == value[-1]
    and value[0] in {'"', "'"}
  )


def is_single_square_wrapper(value: str) -> bool:
  return (
    len(value) >= 2
    and value[0] == "["
    and value[-1] == "]"
    and value.find("]", 1) == len(value) - 1
    and value.rfind("[", 0, -1) == 0
  )


def fix_file(
  path: Path,
  dry_run: bool,
  character_registry: dict[str, dict[str, Any]],
  view_only: bool = False,
) -> Counter[str]:
  original = path.read_bytes()
  counts: Counter[str] = Counter()
  if view_only:
    fixed, counts = strip_view_only_fields(original)
    if fixed != original and not dry_run:
      path.write_bytes(fixed)
    return counts
  url_fixed = fix_url_pointer_file(original, counts)
  if url_fixed is not None:
    if url_fixed != original and not dry_run:
      path.write_bytes(url_fixed)
    return counts

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
  fixed, view_field_counts = strip_view_only_fields(fixed)
  counts.update(view_field_counts)

  try:
    parsed = json.loads(fixed.decode("utf-8-sig"))
  except (UnicodeDecodeError, json.JSONDecodeError):
    parsed = None

  if parsed is not None:
    character_id_counts = expand_character_ids(parsed, character_registry)
    wrapped_text_counts = normalize_wrapped_text_values(parsed)
    reminder_counts = backfill_missing_reminders(parsed)
    if character_id_counts or wrapped_text_counts or reminder_counts:
      counts.update(character_id_counts)
      counts.update(wrapped_text_counts)
      counts.update(reminder_counts)
      fixed = (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

  if fixed != original and not dry_run:
    path.write_bytes(fixed)
  return counts


def fix_url_pointer_file(original: bytes, counts: Counter[str]) -> bytes | None:
  try:
    text = original.decode("utf-8-sig").strip()
  except UnicodeDecodeError:
    return None
  if not URL_POINTER_RE.match(text):
    return None

  try:
    with urllib.request.urlopen(text, timeout=20) as response:
      downloaded = response.read()
    parsed = json.loads(downloaded.decode("utf-8-sig"))
  except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    return original

  counts["url_pointer:downloaded_json"] += 1
  return (json.dumps(parsed, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
  args = parse_args()
  input_dir = Path(args.input_dir)
  paths = json_paths(input_dir, args.file_name)
  character_registry, unresolved_ids = build_character_id_registry(paths)
  total_counts: Counter[str] = Counter()
  changed_files = 0

  for path in paths:
    counts = fix_file(path, args.dry_run, character_registry, args.view_only)
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
  if unresolved_ids:
    print(f"Unresolved character ids: {', '.join(sorted(unresolved_ids))}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
