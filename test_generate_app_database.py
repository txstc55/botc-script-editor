import unittest

from generate_app_database import build_character_id_map


class CharacterIdMapTests(unittest.TestCase):
  def test_maps_exact_ids_and_normalized_image_names(self) -> None:
    rows = [{
      "name": "首席律师",
      "team": "fabled",
      "normalized_team": "fabled",
      "image": "https://example.com/Big_wig.png",
      "source_ids": "scripts/a.json#shouxilvshi",
    }]

    result = build_character_id_map(rows, {("fabled", "首席律师"): "首席律师.json"})

    self.assertEqual("首席律师", result["exact"]["shouxilvshi"]["name"])
    self.assertEqual("首席律师", result["normalized"]["bigwig"]["name"])

  def test_does_not_resolve_ambiguous_generic_ids(self) -> None:
    rows = [
      {
        "name": "甲",
        "team": "townsfolk",
        "normalized_team": "townsfolk",
        "source_ids": "scripts/a.json#diyRole1",
      },
      {
        "name": "乙",
        "team": "demon",
        "normalized_team": "demon",
        "source_ids": "scripts/b.json#diyRole1",
      },
    ]
    filenames = {
      ("townsfolk", "甲"): "甲.json",
      ("demon", "乙"): "乙.json",
    }

    result = build_character_id_map(rows, filenames)

    self.assertNotIn("diyRole1", result["exact"])

  def test_applies_known_id_override(self) -> None:
    target = ("fabled", "首席律师")

    result = build_character_id_map([], {target: "首席律师.json"})

    self.assertEqual("首席律师", result["exact"]["bigwig"]["name"])


if __name__ == "__main__":
  unittest.main()
