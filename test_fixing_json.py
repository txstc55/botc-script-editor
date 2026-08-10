#!/usr/bin/env python3

import unittest

from fixing_json import expand_character_ids, normalized_character_id


class CharacterIdExpansionTest(unittest.TestCase):
  def test_expands_only_known_top_level_ids(self) -> None:
    data = ["chef", "unknown", {"name": "已有角色"}]
    counts = expand_character_ids(data, {
      "chef": {"id": "chef", "name": "厨师", "team": "townsfolk"},
    })
    self.assertEqual(data[0]["name"], "厨师")
    self.assertEqual(data[1], "unknown")
    self.assertEqual(sum(counts.values()), 1)

  def test_normalizes_separator_variants(self) -> None:
    self.assertEqual(normalized_character_id("lil_monsta"), "lilmonsta")

  def test_drops_string_when_full_character_exists(self) -> None:
    data = ["chef", {"id": "custom", "name": "厨师", "team": "townsfolk"}]
    counts = expand_character_ids(data, {
      "chef": {"id": "chef", "name": "厨师", "team": "townsfolk"},
    })
    self.assertEqual(len(data), 1)
    self.assertEqual(data[0]["id"], "custom")
    self.assertEqual(counts["duplicate_character_id:chef"], 1)


if __name__ == "__main__":
  unittest.main()
