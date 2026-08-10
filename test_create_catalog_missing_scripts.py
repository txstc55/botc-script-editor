#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

from create_catalog_missing_scripts import (
  best_variant,
  detected_author,
  ordered_details,
  update_match_overrides,
)


class MissingCatalogCandidateTests(unittest.TestCase):
  def test_best_variant_uses_board_wording(self) -> None:
    value, coverage = best_variant(["旧能力文本", "原图中的完整能力文本"], "角色名 原图中的完整能力文本")

    self.assertEqual(value, "原图中的完整能力文本")
    self.assertEqual(coverage, 1.0)

  def test_board_order_is_team_then_left_and_right_columns(self) -> None:
    details = [
      {"name": "右二", "team": "townsfolk", "x": 0.6, "y": 0.5},
      {"name": "左二", "team": "townsfolk", "x": 0.1, "y": 0.5},
      {"name": "右一", "team": "townsfolk", "x": 0.6, "y": 0.8},
      {"name": "左一", "team": "townsfolk", "x": 0.1, "y": 0.8},
    ]

    self.assertEqual(
      [detail["name"] for detail in ordered_details(details)],
      ["左一", "左二", "右一", "右二"],
    )

  def test_author_stops_before_support_text(self) -> None:
    lines = [{"text": "剧本作者： 星火乐 支持7-15人"}]

    self.assertEqual(detected_author(lines), "星火乐")

  def test_explicit_null_override_is_not_replaced(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "overrides.json"
      path.write_text(json.dumps({"1": None}), encoding="utf-8")

      with self.assertRaises(ValueError):
        update_match_overrides(path, {"1": "all_jsons/测试.json"})


if __name__ == "__main__":
  unittest.main()
