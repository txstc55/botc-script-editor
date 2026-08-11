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

  def test_rebuild_can_copy_roles_from_verified_script(self):
    target = json.dumps([
      {"id": "_meta", "name": "目标剧本"},
      {"name": "旧角色", "team": "townsfolk"},
      {"name": "角色甲&角色乙", "team": "jinx", "ability": "目标相克"},
    ], ensure_ascii=False)
    source = [
      {"id": "_meta", "name": "来源剧本", "notes": ["来源说明"]},
      {"name": "角色甲", "team": "townsfolk", "setup": True},
      {"name": "来源相克", "team": "jinx", "ability": "不应复制"},
    ]

    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "source.json"
      path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
      rebuilt, changed = rebuild_full_roster(target, {
        "source_json": str(path),
        "meta_fields": ["notes"],
      })

    data = json.loads(rebuilt)
    self.assertTrue(changed)
    self.assertEqual(data[0]["name"], "目标剧本")
    self.assertEqual(data[0]["notes"], ["来源说明"])
    self.assertEqual(data[1], {"name": "角色甲", "team": "townsfolk", "setup": 1})
    self.assertEqual(data[2]["ability"], "目标相克")

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

  def test_patch_preserves_inline_object_separator(self):
    source = """[{
\t\t\"id\": \"_meta\",
\t\t\"name\": \"测试剧本\"
\t}, {
\t\t\"id\": \"角色甲\",
\t\t\"name\": \"角色甲\",
\t\t\"team\": \"townsfolk\",
\t\t\"ability\": \"旧能力\"
\t}]
"""

    updated, changes = apply_fix(source, {"additions": [{
      "name": "角色甲",
      "team": "townsfolk",
      "patch": {"ability": "新能力"},
    }]})

    self.assertEqual(changes, ["更新 角色甲"])
    self.assertEqual(json.loads(updated)[1]["ability"], "新能力")

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

  def test_team_order_reorders_existing_roles_and_is_idempotent(self):
    source = json.dumps([
      {"id": "_meta", "name": "测试剧本"},
      {"id": "b", "name": "角色乙", "team": "minion", "ability": "乙"},
      {"id": "a", "name": "角色甲", "team": "minion", "ability": "甲"},
      {"id": "d", "name": "恶魔", "team": "demon"},
    ], ensure_ascii=False, indent=2)
    fix = {"team_order": [{"team": "minion", "names": ["角色甲", "角色乙"]}]}

    updated, changes = apply_fix(source, fix)
    unchanged, second_changes = apply_fix(updated, fix)

    self.assertEqual(changes, ["重排 minion 阵容"])
    self.assertEqual(second_changes, [])
    self.assertEqual(unchanged, updated)
    self.assertEqual(
      [item["name"] for item in json.loads(updated) if item.get("team") == "minion"],
      ["角色甲", "角色乙"],
    )

  def test_source_sync_merges_roles_and_normalizes_source_values(self):
    source = json.dumps([
      {"id": "_meta", "name": "来源剧本"},
      {
        "id": "source-role",
        "name": "旅行角色",
        "team": "traveller",
        "ability": "来源能力",
        "setup": True,
      },
    ], ensure_ascii=False)
    target = json.dumps([
      {"id": "_meta", "name": "目标剧本"},
      {
        "id": "target-role",
        "name": "旅行角色",
        "team": "traveler",
        "ability": "旧能力",
        "remindersGlobal": [],
      },
    ], ensure_ascii=False, indent=2)

    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "source.json"
      path.write_text(source, encoding="utf-8")
      fix = {
        "source_sync": str(path),
        "additions": [{
          "name": "旅行角色",
          "team": "traveler",
          "patch": {"ability": "原图覆盖能力"},
        }],
      }
      updated, changes = apply_fix(target, fix)
      unchanged, second_changes = apply_fix(updated, fix)

    role = json.loads(updated)[1]
    self.assertEqual(changes, ["从来源同步 1 个角色", "更新 旅行角色"])
    self.assertEqual(second_changes, [])
    self.assertEqual(unchanged, updated)
    self.assertEqual(role["ability"], "原图覆盖能力")
    self.assertEqual(role["team"], "traveler")
    self.assertEqual(role["setup"], 1)
    self.assertEqual(role["remindersGlobal"], [])


if __name__ == "__main__":
  unittest.main()
