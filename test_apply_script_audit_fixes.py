import json
import unittest

from apply_script_audit_fixes import rebuild_full_roster


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


if __name__ == "__main__":
  unittest.main()
