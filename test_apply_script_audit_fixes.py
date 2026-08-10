import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apply_script_audit_fixes import apply_fix, database_role, rebuild_full_roster


class FullRosterTest(unittest.TestCase):
  def test_rebuild_preserves_meta_and_jinxes(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {},
      {"name": "旧角色", "team": "townsfolk"},
      {"name": "角色甲&角色乙", "team": "jinx", "ability": "相克"},
    ], ensure_ascii=False)
    roster = {
      "entries": [{
        "entry": {"id": "角色甲", "name": "角色甲", "team": "townsfolk"},
      }],
    }

    rebuilt, changed = rebuild_full_roster(source, roster)
    data = json.loads(rebuilt)

    self.assertTrue(changed)
    self.assertEqual([item.get("name") for item in data], ["测试剧本", "角色甲", "角色甲&角色乙"])
    self.assertFalse(rebuild_full_roster(rebuilt, roster)[1])

  def test_remove_entry_by_id(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {"id": "old-rule", "name": "", "team": "jinx", "ability": "旧规则"},
      {"id": "角色甲", "name": "角色甲", "team": "townsfolk"},
    ], ensure_ascii=False, indent=2)

    updated, changes = apply_fix(source, {"removals": [{"id": "old-rule"}]})

    self.assertEqual(changes, ["移除 old-rule"])
    self.assertEqual([item["id"] for item in json.loads(updated)], ["_meta", "角色甲"])

  def test_add_entry_before_existing_role(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {"id": "b", "name": "角色乙", "team": "townsfolk"},
    ], ensure_ascii=False, indent=2)
    addition = {
      "entry": {"id": "a", "name": "角色甲", "team": "townsfolk"},
      "before": {"name": "角色乙", "team": "townsfolk"},
    }

    updated, changes = apply_fix(source, {"additions": [addition]})

    self.assertEqual(changes, ["新增 角色甲"])
    self.assertEqual([item["id"] for item in json.loads(updated)], ["_meta", "a", "b"])

  def test_explicit_addition_updates_existing_entry(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {"id": "a&b", "name": "角色甲&角色乙", "team": "jinx", "ability": "旧规则"},
    ], ensure_ascii=False, indent=2)
    replacement = {
      "entry": {
        "id": "a&b",
        "name": "角色甲&角色乙",
        "team": "jinx",
        "ability": "新规则",
      },
    }

    updated, changes = apply_fix(source, {"additions": [replacement]})

    self.assertEqual(changes, ["更新 角色甲&角色乙"])
    self.assertEqual(json.loads(updated)[1]["ability"], "新规则")

  def test_database_role_applies_script_specific_overrides(self):
    rows = {
      ("角色甲", "townsfolk"): [{
        "name": "角色甲",
        "team": "townsfolk",
        "normalized_team": "townsfolk",
        "ability": "能力",
        "occurrence_count": "1",
      }],
    }

    with patch("apply_script_audit_fixes.database_rows", return_value=rows):
      role = database_role({
        "name": "角色甲",
        "team": "townsfolk",
        "overrides": {"firstNight": 4},
      })

    self.assertEqual(role["firstNight"], 4)

  def test_source_json_role_applies_script_specific_overrides(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "source.json"
      path.write_text(json.dumps([
        {"name": "角色甲", "team": "townsfolk", "firstNight": 1},
      ], ensure_ascii=False), encoding="utf-8")

      role = database_role({
        "source_json": str(path),
        "name": "角色甲",
        "team": "townsfolk",
        "overrides": {"firstNight": 4},
      })

    self.assertEqual(role["firstNight"], 4)

  def test_database_override_updates_existing_entry(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {"id": "角色甲", "name": "角色甲", "team": "townsfolk", "firstNight": 0},
    ], ensure_ascii=False, indent=2)
    rows = {
      ("角色甲", "townsfolk"): [{
        "name": "角色甲",
        "team": "townsfolk",
        "normalized_team": "townsfolk",
        "ability": "能力",
        "occurrence_count": "1",
      }],
    }

    with patch("apply_script_audit_fixes.database_rows", return_value=rows):
      updated, changes = apply_fix(source, {"additions": [{
        "name": "角色甲",
        "team": "townsfolk",
        "overrides": {"firstNight": 4},
      }]})

    self.assertEqual(changes, ["更新 角色甲"])
    self.assertEqual(json.loads(updated)[1]["firstNight"], 4)

  def test_patch_updates_existing_entry_without_replacing_other_fields(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {
        "id": "角色甲",
        "name": "角色甲",
        "team": "townsfolk",
        "ability": "剧本专属能力",
        "firstNight": 0,
      },
    ], ensure_ascii=False, indent=2)

    updated, changes = apply_fix(source, {"additions": [{
      "name": "角色甲",
      "team": "townsfolk",
      "patch": {"firstNight": 4},
    }]})

    role = json.loads(updated)[1]
    self.assertEqual(changes, ["更新 角色甲"])
    self.assertEqual(role["ability"], "剧本专属能力")
    self.assertEqual(role["firstNight"], 4)

  def test_meta_updates_replace_selected_fields(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本", "author": "旧作者"},
      {"id": "角色甲", "name": "角色甲", "team": "townsfolk"},
    ], ensure_ascii=False, indent=2)

    updated, changes = apply_fix(source, {
      "meta_updates": {"author": "新作者"},
    })

    self.assertEqual(changes, ["更新剧本信息 author"])
    self.assertEqual(json.loads(updated)[0]["author"], "新作者")


if __name__ == "__main__":
  unittest.main()
