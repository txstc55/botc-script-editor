#!/usr/bin/env python3

import json
import unittest

from fixing_json import fix_file, strip_view_only_fields


class FixingJsonTests(unittest.TestCase):
  def test_strip_view_fields_keeps_standard_fields(self) -> None:
    source = [{
      "id": "_meta",
      "name": "[保留名称]",
      "notes": [{"text": "说明", "html": "<b>说明</b>"}],
    }, {
      "name": "角色",
      "team": "townsfolk",
      "abilityHtml": "<b>能力</b>",
      "previewSection": "thirdParty",
      "reminders": ["[保留标签]"],
    }]

    fixed, counts = strip_view_only_fields(json.dumps(source, ensure_ascii=False, indent=2).encode())
    data = json.loads(fixed)

    self.assertEqual(data[0], {"id": "_meta", "name": "[保留名称]"})
    self.assertEqual(data[1]["reminders"], ["[保留标签]"])
    self.assertEqual(counts["view_field:notes"], 1)
    self.assertEqual(counts["view_field:abilityHtml"], 1)
    self.assertEqual(counts["view_field:previewSection"], 1)

  def test_view_only_does_not_run_other_normalization(self) -> None:
    with self.subTest("boolean setup remains unchanged"):
      from pathlib import Path
      import tempfile

      with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "script.json"
        path.write_text(json.dumps([{
          "id": "_meta",
          "notes": [{"text": "说明"}],
        }, {
          "name": "角色",
          "team": "townsfolk",
          "setup": True,
        }], ensure_ascii=False, indent=2), encoding="utf-8")

        fix_file(path, False, {}, view_only=True)

        self.assertIs(json.loads(path.read_text())[1]["setup"], True)


if __name__ == "__main__":
  unittest.main()
