#!/usr/bin/env python3
"""Create high-confidence JSON candidates for unmatched Bilibili script boards."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from audit_bilibili_scripts import (
  build_ocr_tool,
  clean_space,
  ngram_coverage,
  ocr_lines,
  read_catalog,
)


ROOT = Path(__file__).resolve().parent
CHARACTER_ROOT = ROOT / "script_editor" / "public" / "characters"
TEAM_FOLDERS = {
  "townsfolk": "townsfolks",
  "outsider": "outsiders",
  "minion": "minions",
  "demon": "demons",
  "traveler": "travelers",
  "fabled": "fabled",
}
TEAM_ORDER = tuple(TEAM_FOLDERS)
PATH_TRANSLATION = str.maketrans({
  "/": "／",
  "\\": "＼",
  ":": "：",
  "*": "＊",
  "?": "？",
  '"': "＂",
  "<": "＜",
  ">": "＞",
  "|": "｜",
})


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--audit-root", type=Path, default=Path("bilibili_script_audit"))
  parser.add_argument("--output", type=Path, default=Path("all_jsons/来源核对补全"))
  parser.add_argument("--minimum-coverage", type=float, default=0.45)
  parser.add_argument("--opus-id", action="append", default=[])
  parser.add_argument("--apply", action="store_true")
  return parser.parse_args()


def first_variant(data: dict[str, Any], trait: str, default: Any) -> Any:
  values = data.get("variants", {}).get(trait, [])
  return values[0] if values else default


def best_variant(values: list[Any], board_text: str) -> tuple[str, float]:
  candidates = [clean_space(value) for value in values if clean_space(value)]
  if not candidates:
    return "", 0.0
  value = max(candidates, key=lambda candidate: ngram_coverage(candidate, board_text))
  return value, ngram_coverage(value, board_text)


def ordered_details(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
  unique: dict[tuple[str, str], dict[str, Any]] = {}
  for detail in details:
    identity = (clean_space(detail.get("name")), clean_space(detail.get("team")))
    if identity[0] and identity not in unique:
      unique[identity] = detail
  return sorted(unique.values(), key=lambda detail: (
    TEAM_ORDER.index(clean_space(detail.get("team")))
    if clean_space(detail.get("team")) in TEAM_ORDER else len(TEAM_ORDER),
    0 if float(detail.get("x", 0)) < 0.4 else 1,
    -float(detail.get("y", 0)),
  ))


def role_entry(
  detail: dict[str, Any],
  board_text: str,
) -> tuple[dict[str, Any], float]:
  name = clean_space(detail.get("name"))
  team = clean_space(detail.get("team"))
  folder = TEAM_FOLDERS.get(team)
  if not folder:
    raise ValueError(f"角色团队无法解析：{name}/{team or 'empty'}")
  path = CHARACTER_ROOT / folder / f"{name}.json"
  if not path.exists():
    raise ValueError(f"角色数据库中不存在：{name}/{team}")
  data = json.loads(path.read_text(encoding="utf-8"))
  ability, coverage = best_variant(data.get("variants", {}).get("ability", []), board_text)
  if not ability:
    raise ValueError(f"角色没有能力文本：{name}/{team}")
  first_night = first_variant(data, "firstNight", 0)
  other_night = first_variant(data, "otherNight", 0)
  first_reminder = first_variant(data, "firstNightReminder", "")
  other_reminder = first_variant(data, "otherNightReminder", "")
  return {
    "id": name,
    "name": name,
    "edition": "custom",
    "team": team,
    "ability": ability,
    "image": first_variant(data, "image", ""),
    "firstNight": first_night,
    "firstNightReminder": first_reminder or (ability if first_night else ""),
    "otherNight": other_night,
    "otherNightReminder": other_reminder or (ability if other_night else ""),
    "reminders": first_variant(data, "reminders", []),
    "remindersGlobal": first_variant(data, "remindersGlobal", []),
    "setup": int(bool(first_variant(data, "setup", 0))),
    "flavor": first_variant(data, "flavor", ""),
  }, coverage


def detected_author(lines: list[dict[str, Any]]) -> str:
  for line in lines:
    text = clean_space(line.get("text"))
    match = re.search(r"剧本作者[：:]?\s*(.+?)(?:\s+支持|$)", text)
    if match:
      return clean_space(match.group(1)).strip("·|-—")
  return ""


def safe_name(value: str) -> str:
  return clean_space(value).translate(PATH_TRANSLATION).strip(". ") or "未命名剧本"


def candidate_for_folder(
  folder: Path,
  script_name: str,
  minimum_coverage: float,
  ocr_binary: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  metadata = json.loads((folder / "核对状态.json").read_text(encoding="utf-8"))
  reference_name = clean_space(metadata.get("ocr_reference_image"))
  reference = folder / reference_name
  if not reference.exists():
    raise ValueError("缺少 OCR 参考图")
  lines = ocr_lines(ocr_binary, reference)
  board_text = "\n".join(clean_space(line.get("text")) for line in lines)
  details = ordered_details(metadata.get("ocr_heading_character_details", []))
  if len(details) < 8:
    raise ValueError(f"识别角色不足：{len(details)}")
  entries: list[dict[str, Any]] = []
  coverages: dict[str, float] = {}
  for detail in details:
    entry, coverage = role_entry(detail, board_text)
    entries.append(entry)
    coverages[f"{entry['team']}/{entry['name']}"] = round(coverage, 4)
  weak = [name for name, coverage in coverages.items() if coverage < minimum_coverage]
  if weak:
    raise ValueError(f"能力 OCR 覆盖率不足：{', '.join(weak)}")
  meta: dict[str, Any] = {"id": "_meta", "name": script_name}
  author = detected_author(lines)
  if author:
    meta["author"] = author
  return [meta, *entries], {
    "reference_image": str(reference),
    "role_count": len(entries),
    "minimum_ability_coverage": min(coverages.values()),
    "ability_coverages": coverages,
  }


def update_match_overrides(path: Path, additions: dict[str, str]) -> None:
  overrides = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
  for opus_id, target in additions.items():
    existing = overrides.get(opus_id)
    if opus_id in overrides and existing != target:
      raise ValueError(f"匹配覆盖冲突：{opus_id}: {existing} != {target}")
    overrides[opus_id] = target
  ordered = dict(sorted(overrides.items(), key=lambda item: int(item[0])))
  path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
  args = parse_args()
  catalog = read_catalog(args.audit_root / "剧本清单.json")
  ocr_binary = build_ocr_tool(args.audit_root)
  overrides_path = ROOT / "bilibili_match_overrides.json"
  overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
  selected_ids = set(args.opus_id)
  report: list[dict[str, Any]] = []
  matches: dict[str, str] = {}
  for item in catalog:
    if selected_ids and item.opus_id not in selected_ids:
      continue
    if item.status == "matched" or "角色合集" in item.title:
      continue
    folders = list((args.audit_root / "剧本").glob(f"*-{item.opus_id}"))
    output = args.output / f"#{safe_name(item.script_name)}-{item.opus_id}.json"
    record: dict[str, Any] = {
      "opus_id": item.opus_id,
      "script_name": item.script_name,
      "output": str(output),
    }
    try:
      if item.opus_id in overrides:
        raise ValueError(f"已有人工匹配覆盖：{overrides[item.opus_id]}")
      if len(folders) != 1:
        raise ValueError(f"来源文件夹数量不是1：{len(folders)}")
      payload, evidence = candidate_for_folder(
        folders[0], item.script_name, args.minimum_coverage, ocr_binary,
      )
      record.update(status="candidate", **evidence)
      if args.apply:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        matches[item.opus_id] = str(output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
      record.update(status="rejected", reason=str(error))
    report.append(record)
  report_path = args.audit_root / "缺失JSON候选.json"
  report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  if args.apply and matches:
    update_match_overrides(overrides_path, matches)
  candidates = sum(record["status"] == "candidate" for record in report)
  print(f"候选 {candidates} 个，拒绝 {len(report) - candidates} 个。")
  if args.apply:
    print(f"写入 JSON {len(matches)} 个。")


if __name__ == "__main__":
  main()
