#!/usr/bin/env python3
"""Apply only high-confidence missing jinx rules from the audit report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from apply_script_audit_fixes import apply_fix


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--report",
    type=Path,
    default=Path("bilibili_script_audit/缺失相克候选.json"),
  )
  parser.add_argument(
    "--manual",
    type=Path,
    default=Path("bilibili_jinx_fixes.json"),
  )
  parser.add_argument("--apply", action="store_true")
  return parser.parse_args()


def role_image(data: Any, name: str) -> str:
  if not isinstance(data, list):
    return ""
  for item in data:
    if isinstance(item, dict) and item.get("name") == name:
      return str(item.get("image", ""))
  return ""


def high_confidence_entry(candidate: dict[str, Any], data: Any) -> dict[str, Any] | None:
  match = candidate.get("database_match")
  host = str(candidate.get("host", "")).strip()
  if not isinstance(match, dict) or float(match.get("score", 0)) < 0.75:
    return None
  database_targets = [str(value).strip() for value in match.get("targets", []) if str(value).strip()]
  detected = list(dict.fromkeys(
    str(value).strip() for value in candidate.get("targets", []) if str(value).strip()
  ))
  if len(detected) >= 2 and set(detected) == set(database_targets):
    targets = detected
  elif host in database_targets and len(database_targets) >= 2:
    targets = database_targets
  else:
    return None
  name = "&".join(targets)
  return {
    "id": name,
    "name": name,
    "team": "jinx",
    "ability": str(match.get("ability", "")).strip(),
    "image": role_image(data, host),
    "setup": 0,
  }


def main() -> None:
  args = parse_args()
  report = json.loads(args.report.read_text(encoding="utf-8"))
  manual = json.loads(args.manual.read_text(encoding="utf-8")) if args.manual.exists() else {}
  manual_by_target = {
    target: fix
    for fix in manual.get("fixes", [])
    for target in fix.get("targets", [])
  }
  changed_files = 0
  added_rules = 0
  processed_targets: set[str] = set()
  for script in report if isinstance(report, list) else []:
    target = Path(str(script.get("local_json", "")))
    if not target.exists():
      continue
    processed_targets.add(str(target))
    raw = target.read_text(encoding="utf-8")
    data = json.loads(raw)
    additions = []
    for candidate in script.get("candidates", []):
      if not isinstance(candidate, dict):
        continue
      entry = high_confidence_entry(candidate, data)
      if entry:
        additions.append({"entry": entry})
    fix = dict(manual_by_target.get(str(target), {}))
    fix["additions"] = [*fix.get("additions", []), *additions]
    updated, changes = apply_fix(raw, fix)
    if not changes:
      continue
    changed_files += 1
    added_rules += len(changes)
    print(f"{'写入' if args.apply else '待写入'}：{target}：{'; '.join(changes)}")
    if args.apply:
      target.write_text(updated, encoding="utf-8")
  for target_value, fix in manual_by_target.items():
    if target_value in processed_targets:
      continue
    target = Path(target_value)
    if not target.exists():
      continue
    raw = target.read_text(encoding="utf-8")
    updated, changes = apply_fix(raw, fix)
    if not changes:
      continue
    changed_files += 1
    added_rules += len(changes)
    print(f"{'写入' if args.apply else '待写入'}：{target}：{'; '.join(changes)}")
    if args.apply:
      target.write_text(updated, encoding="utf-8")
  print(f"剧本文件 {changed_files} 个，相克规则 {added_rules} 条。")


if __name__ == "__main__":
  main()
