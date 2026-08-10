#!/usr/bin/env python3
"""Build roster candidates when per-team counts move but the board total is stable."""

from __future__ import annotations

import json
from pathlib import Path

from audit_bilibili_scripts import build_ocr_tool, clean_space, ngram_coverage, ocr_lines
from extract_audit_role_replacements import character_rows, row_entry
from extract_audit_roster_replacements import ROOT, current_roles, source_order


CORE_TEAMS = {"townsfolk", "outsider", "minion", "demon"}


def main() -> None:
  summary = json.loads((ROOT / "核对汇总.json").read_text(encoding="utf-8"))
  rows = character_rows()
  ocr_binary = build_ocr_tool(ROOT)
  candidates = []
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
    team_orders = {
      team: source_order(metadata.get("ocr_heading_character_details", []), team)
      for team in CORE_TEAMS
    }
    current_total = sum(len(roles_by_team.get(team, [])) for team in CORE_TEAMS)
    source_total = sum(len(team_orders[team]) for team in CORE_TEAMS)
    changed_teams = [
      team for team in CORE_TEAMS
      if team_orders[team]
      and set(team_orders[team]) != {
        clean_space(item.get("name")) for item in roles_by_team.get(team, [])
      }
    ]
    if current_total != source_total or not changed_teams or all(
      len(team_orders[team]) == len(roles_by_team.get(team, []))
      for team in changed_teams
    ):
      continue
    board_text = "\n".join(
      clean_space(line.get("text"))
      for line in ocr_lines(ocr_binary, folder / image_name)
    )
    for team in changed_teams:
      existing_by_name = {
        clean_space(item.get("name")): item for item in roles_by_team.get(team, [])
      }
      entries = []
      additions = []
      unresolved = []
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
        "old_order": [clean_space(item.get("name")) for item in roles_by_team.get(team, [])],
        "new_order": team_orders[team],
        "removed_names": sorted(set(existing_by_name) - set(team_orders[team])),
        "additions": additions,
        "unresolved_names": unresolved,
        "minimum_addition_coverage": round(min(
          (item["ability_coverage"] for item in additions),
          default=1,
        ), 4),
        "entries": entries,
      })

  output = ROOT / "角色跨阵营候选.json"
  output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  complete = [item for item in candidates if not item["unresolved_names"]]
  high = [item for item in complete if item["minimum_addition_coverage"] >= 0.65]
  print(f"跨阵营候选 {len(candidates)} 组，数据完整 {len(complete)} 组，高置信度 {len(high)} 组。")
  print(output)


if __name__ == "__main__":
  main()
