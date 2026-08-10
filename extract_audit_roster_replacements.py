#!/usr/bin/env python3
"""Build reviewed-ready, equal-size team roster replacements from source boards."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from audit_bilibili_scripts import build_ocr_tool, clean_space, ngram_coverage, ocr_lines
from extract_audit_role_replacements import character_rows, row_entry


ROOT = Path("bilibili_script_audit")
ROLE_TEAMS = {"townsfolk", "outsider", "minion", "demon", "fabled"}


def current_roles(data: Any) -> dict[str, list[dict[str, Any]]]:
  result: dict[str, list[dict[str, Any]]] = defaultdict(list)
  if not isinstance(data, list):
    return result
  for item in data:
    if not isinstance(item, dict):
      continue
    team = clean_space(item.get("team")).lower()
    if team in ROLE_TEAMS:
      result[team].append(item)
  return result


def source_order(details: list[dict[str, Any]], team: str) -> list[str]:
  team_details = [item for item in details if item.get("team") == team]
  team_details.sort(key=lambda item: (0 if float(item.get("x", 0)) < 0.45 else 1, -float(item.get("y", 0))))
  return list(dict.fromkeys(clean_space(item.get("name")) for item in team_details if clean_space(item.get("name"))))


def main() -> None:
  summary = json.loads((ROOT / "核对汇总.json").read_text(encoding="utf-8"))
  rows = character_rows()
  ocr_binary = build_ocr_tool(ROOT)
  candidates: list[dict[str, Any]] = []
  for summary_item in summary.get("items", []):
    if summary_item.get("status") == "missing_json":
      continue
    folder = Path(summary_item["folder"])
    metadata = json.loads((folder / "核对状态.json").read_text(encoding="utf-8"))
    local_json_value = clean_space(metadata.get("local_json"))
    local_json = Path(local_json_value)
    image_name = clean_space(metadata.get("ocr_reference_image"))
    if not local_json_value or not local_json.is_file() or not image_name:
      continue
    data = json.loads(local_json.read_text(encoding="utf-8"))
    roles_by_team = current_roles(data)
    details = metadata.get("ocr_heading_character_details", [])
    team_orders = {
      team: source_order(details, team) for team in ROLE_TEAMS
    }
    changed_teams = [
      team for team in ROLE_TEAMS
      if team_orders[team]
      and len(team_orders[team]) == len(roles_by_team.get(team, []))
      and set(team_orders[team]) != {
        clean_space(item.get("name")) for item in roles_by_team.get(team, [])
      }
    ]
    if not changed_teams:
      continue
    board_text = "\n".join(
      clean_space(line.get("text"))
      for line in ocr_lines(ocr_binary, folder / image_name)
    )
    for team in changed_teams:
      existing_by_name = {
        clean_space(item.get("name")): item for item in roles_by_team[team]
      }
      entries: list[dict[str, Any]] = []
      additions: list[dict[str, Any]] = []
      unresolved: list[str] = []
      for name in team_orders[team]:
        if name in existing_by_name:
          entries.append(existing_by_name[name])
          continue
        scored = sorted([
          (
            ngram_coverage(row.get("ability", ""), board_text),
            int(row.get("occurrence_count", 0) or 0),
            row,
          )
          for row in rows.get((name, team), [])
        ], key=lambda value: (value[0], value[1]), reverse=True)
        if not scored:
          unresolved.append(name)
          continue
        score, occurrence_count, row = scored[0]
        entry = row_entry(row)
        entries.append(entry)
        additions.append({
          "name": name,
          "ability_coverage": round(score, 4),
          "occurrence_count": occurrence_count,
          "entry": entry,
        })
      candidates.append({
        "script_name": summary_item["script_name"],
        "opus_id": summary_item["opus_id"],
        "local_json": str(local_json),
        "reference_image": str(folder / image_name),
        "team": team,
        "old_order": [clean_space(item.get("name")) for item in roles_by_team[team]],
        "new_order": team_orders[team],
        "removed_names": sorted(set(existing_by_name) - set(team_orders[team])),
        "additions": additions,
        "unresolved_names": unresolved,
        "minimum_addition_coverage": round(min(
          (item["ability_coverage"] for item in additions),
          default=0,
        ), 4),
        "entries": entries,
      })

  output = ROOT / "角色阵容候选.json"
  output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  complete = [item for item in candidates if not item["unresolved_names"]]
  high = [item for item in complete if item["minimum_addition_coverage"] >= 0.65]
  print(f"阵容候选 {len(candidates)} 组，数据完整 {len(complete)} 组，高置信度 {len(high)} 组。")
  print(output)


if __name__ == "__main__":
  main()
