import unittest

from create_missing_audit_scripts import (
  deadline_approaches,
  devotees_two,
  favonius_mystery_v15,
  orletis_manor,
  return_before_march,
  taotie_feast,
  trial_by_ghost,
)


class MissingAuditScriptTests(unittest.TestCase):
  def test_trial_by_ghost_matches_board_roster(self):
    items = trial_by_ghost()
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "townsfolk"],
      ["小精灵", "灵媒", "共情者", "捉鬼专家", "灵能侦探", "博学者", "摄影记者", "化身幽灵"],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["凶宅"],
    )

  def test_source_jinx_order_is_preserved(self):
    self.assertEqual(
      [item["name"] for item in deadline_approaches() if item.get("team") == "jinx"],
      ["科学怪人&酒鬼", "利维坦&祖母", "暴乱&祖母"],
    )

  def test_nonzero_night_orders_have_reminders(self):
    for items in (
      trial_by_ghost(),
      taotie_feast(),
      deadline_approaches(),
      devotees_two(),
      return_before_march(),
    ):
      for item in items:
        if item.get("firstNight", 0):
          self.assertTrue(item.get("firstNightReminder"), item.get("name"))
        if item.get("otherNight", 0):
          self.assertTrue(item.get("otherNightReminder"), item.get("name"))

  def test_not_first_night_note_has_no_colon(self):
    meta = taotie_feast()[0]
    marker = next(note for note in meta["notes"] if note["text"].startswith("*代表"))
    self.assertEqual(marker["text"], "*代表非首个夜晚")
    self.assertNotIn("：", marker["html"])

  def test_orletis_manor_rebuilds_current_board(self):
    items = orletis_manor()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon")],
      [13, 4, 4, 4],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["摄影师&宿伞白魂"],
    )

  def test_devotees_two_matches_board(self):
    items = devotees_two()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "fabled")],
      [13, 4, 4, 4, 2],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["方古&红唇女郎"],
    )
    patient = next(item for item in items if item.get("name") == "病患")
    self.assertEqual(patient["image"], "/audit_icons/效死之徒Ⅱ/病患.png")

  def test_return_before_march_preserves_source_rules(self):
    items = return_before_march()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon")],
      [13, 4, 4, 4],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["圣洁之魂", "哨兵", "私货商人"],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["驱魔人&暴乱", "炼金术士&召唤师", "镇长&暴乱", "麻脸巫婆&落难少女", "召唤师", "召唤师&工程师"],
    )

  def test_favonius_v15_replaces_old_roster_and_assets(self):
    items = favonius_mystery_v15()
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "townsfolk"],
      ["安柏", "米卡", "九条裟罗", "莫娜", "八重神子", "温迪", "纳西妲", "优菈", "胡桃", "钟离", "琴", "迪卢克", "雷电将军"],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["尘世执政", "执行官"],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["渊上之物&北斗"],
    )
    self.assertTrue(all(
      str(item.get("image", "")).startswith("/audit_icons/西风谜团/")
      for item in items if item.get("team") not in (None, "jinx")
    ))


if __name__ == "__main__":
  unittest.main()
