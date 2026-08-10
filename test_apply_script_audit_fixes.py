import json
import unittest

from apply_script_audit_fixes import apply_fix, rebuild_full_roster


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


if __name__ == "__main__":
  unittest.main()
