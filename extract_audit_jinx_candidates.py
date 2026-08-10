#!/usr/bin/env python3
"""Extract missing jinx rules from reviewed source boards."""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from audit_bilibili_scripts import (
  build_ocr_tool,
  clean_space,
  is_jinx_marker_line,
  json_items,
  normalized_ocr_text,
  ocr_lines,
)


ROOT = Path("bilibili_script_audit")


def load_jinx_database() -> list[dict[str, Any]]:
  records: list[dict[str, Any]] = []
  for path in Path("script_editor/public/jinxes").glob("*.json"):
    if path.name == "index.json":
      continue
    try:
      record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      continue
    if not isinstance(record, dict):
      continue
    abilities = record.get("variants", {}).get("ability", [])
    for ability in abilities if isinstance(abilities, list) else []:
      if clean_space(ability):
        records.append({
          "name": clean_space(record.get("name")),
          "targets": [clean_space(value) for value in record.get("targets", [])],
          "ability": clean_space(ability),
        })
  return records


def script_context(path: Path) -> tuple[list[str], list[str]]:
  data = json.loads(path.read_text(encoding="utf-8"))
  names: list[str] = []
  jinx_abilities: list[str] = []
  for item in json_items(data):
    team = clean_space(item.get("team")).lower()
    name = clean_space(item.get("name"))
    if "jinx" in team:
      ability = clean_space(item.get("ability"))
      if ability:
        jinx_abilities.append(ability)
      continue
    if name and clean_space(item.get("id")) != "_meta":
      names.append(name)
    for nested in item.get("jinxes", []) if isinstance(item.get("jinxes"), list) else []:
      if isinstance(nested, dict):
        ability = clean_space(nested.get("reason") or nested.get("ability"))
        if ability:
          jinx_abilities.append(ability)
  return list(dict.fromkeys(names)), jinx_abilities


def text_similarity(left: str, right: str) -> float:
  normalized_left = normalized_ocr_text(left)
  normalized_right = normalized_ocr_text(right)
  if not normalized_left or not normalized_right:
    return 0.0
  return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def rule_snippet(marker: dict[str, Any], lines: list[dict[str, Any]]) -> str:
  marker_y = float(marker.get("y", 0))
  marker_x = float(marker.get("x", 0))
  column_left, column_right = (0.0, 0.5) if marker_x < 0.5 else (0.5, 1.0)
  nearby = [
    line for line in lines
    if marker_y - 0.032 <= float(line.get("y", 0)) <= marker_y + 0.008
    and column_left <= float(line.get("x", 0)) < column_right
  ]
  nearby.sort(key=lambda line: (-round(float(line.get("y", 0)), 3), float(line.get("x", 0))))
  text = clean_space("".join(clean_space(line.get("text")) for line in nearby))
  if is_jinx_marker_line(text) and any(separator in text for separator in "：:"):
    text = text.split("：", 1)[-1] if "：" in text else text.split(":", 1)[-1]
  if "）" in text:
    text = text.split("）", 1)[0]
  return text.strip("()（） ")


def nearest_host(marker: dict[str, Any], lines: list[dict[str, Any]], names: list[str]) -> str:
  marker_y = float(marker.get("y", 0))
  marker_x = float(marker.get("x", 0))
  same_column = lambda x: (x < 0.5) == (marker_x < 0.5)
  candidates = [
    (float(line.get("y", 0)) - marker_y, clean_space(line.get("text")))
    for line in lines
    if clean_space(line.get("text")) in names
    and float(line.get("y", 0)) > marker_y
    and same_column(float(line.get("x", 0)))
  ]
  return min(candidates)[1] if candidates else ""


def detected_targets(text: str, host: str, names: list[str]) -> list[str]:
  positions = sorted(
    (text.find(name), name) for name in names if name and name in text
  )
  text_targets = list(dict.fromkeys(name for _, name in positions))
  if len(text_targets) >= 2 or not host or host in text_targets:
    return text_targets
  return [host, *text_targets]


def best_database_match(
  text: str,
  targets: list[str],
  play_names: set[str],
  records: list[dict[str, Any]],
) -> dict[str, Any] | None:
  target_set = set(targets)
  candidates: list[tuple[float, dict[str, Any]]] = []
  for record in records:
    record_targets = set(record["targets"])
    if record_targets and not record_targets <= play_names:
      continue
    if target_set and record_targets and not target_set <= record_targets and not record_targets <= target_set:
      continue
    candidates.append((text_similarity(text, record["ability"]), record))
  if not candidates:
    return None
  score, record = max(candidates, key=lambda value: value[0])
  return {**record, "score": round(score, 4)} if score >= 0.55 else None


def main() -> None:
  summary = json.loads((ROOT / "核对汇总.json").read_text(encoding="utf-8"))
  records = load_jinx_database()
  ocr_binary = build_ocr_tool(ROOT)
  scripts: list[dict[str, Any]] = []
  for item in summary.get("items", []):
    missing_count = int(item.get("missing_jinx_rule_count", 0) or 0)
    if missing_count <= 0:
      continue
    folder = Path(item["folder"])
    metadata = json.loads((folder / "核对状态.json").read_text(encoding="utf-8"))
    json_path = folder / "整理后.json"
    image_name = clean_space(metadata.get("ocr_reference_image"))
    if not json_path.exists() or not image_name:
      continue
    names, existing_abilities = script_context(json_path)
    candidates: list[dict[str, Any]] = []
    image_names = [image_name]
    for source in metadata.get("ocr_source_images", []):
      source_name = clean_space(source.get("image"))
      if not source_name or source_name == image_name:
        continue
      if len(source.get("heading_characters", [])) >= 8:
        continue
      source_lines = ocr_lines(ocr_binary, folder / source_name)
      if any(is_jinx_marker_line(line.get("text")) for line in source_lines):
        image_names.append(source_name)
    seen_candidates: set[tuple[str, str, tuple[str, ...]]] = set()
    for source_name in image_names:
      lines = ocr_lines(ocr_binary, folder / source_name)
      for marker in [line for line in lines if is_jinx_marker_line(line.get("text"))]:
        text = rule_snippet(marker, lines)
        if not text or any(text_similarity(text, ability) >= 0.6 for ability in existing_abilities):
          continue
        host = nearest_host(marker, lines, names)
        targets = detected_targets(text, host, names)
        candidate_key = (normalized_ocr_text(text), host, tuple(targets))
        if candidate_key in seen_candidates:
          continue
        seen_candidates.add(candidate_key)
        match = best_database_match(text, targets, set(names), records)
        candidates.append({
          "image": source_name,
          "host": host,
          "targets": targets,
          "ocr_text": text,
          "database_match": match,
          "x": round(float(marker.get("x", 0)), 4),
          "y": round(float(marker.get("y", 0)), 4),
        })
    scripts.append({
      "script_name": item["script_name"],
      "opus_id": item["opus_id"],
      "local_json": metadata.get("local_json", ""),
      "reference_image": str(folder / image_name),
      "missing_jinx_rule_count": missing_count,
      "candidates": candidates,
    })

  output = ROOT / "缺失相克候选.json"
  output.write_text(json.dumps(scripts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  candidate_count = sum(len(item["candidates"]) for item in scripts)
  matched_count = sum(
    bool(candidate["database_match"])
    for item in scripts for candidate in item["candidates"]
  )
  print(f"剧本 {len(scripts)} 个，候选 {candidate_count} 条，数据库匹配 {matched_count} 条。")
  print(output)


if __name__ == "__main__":
  main()
