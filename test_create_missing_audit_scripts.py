import unittest

from create_missing_audit_scripts import (
  battle_of_hogwarts,
  deadline_approaches,
  devotees_two,
  favonius_mystery_v15,
  medieval_mythos,
  myth_of_babylon,
  orletis_manor,
  return_before_march,
  taotie_feast,
  ten_days_end,
  trial_by_ghost,
  until_morale_improves,
  wizards_meet,
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

  def test_medieval_mythos_preserves_source_roster_and_night_order(self):
    items = medieval_mythos()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "fabled")],
      [13, 4, 4, 4, 1],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["古老魔法"],
    )
    self.assertEqual(
      [item["name"] for item in sorted(
        (item for item in items if item.get("firstNight", 0)),
        key=lambda item: item["firstNight"],
      )],
      ["傀儡师", "缪斯", "王子", "侍童", "侍从", "魔法师", "天选之子", "被诅咒者"],
    )

  def test_wizards_meet_corrects_source_metadata_and_orders(self):
    items = wizards_meet()
    self.assertEqual(items[0]["name"], "魔法祭典")
    self.assertIn("LemonSneeze", items[0]["author"])
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "traveler", "fabled")],
      [13, 4, 4, 4, 5, 4],
    )
    self.assertTrue(all(
      isinstance(item.get(field, 0), int)
      for item in items[1:]
      for field in ("firstNight", "otherNight")
    ))

  def test_ten_days_end_preserves_board_roster_rules_and_night_order(self):
    items = ten_days_end()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "fabled")],
      [13, 4, 5, 4, 1],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["灵嗅&招灾", "夺心魄&一念之间", "招灾&激发&疯长", "饕餮&魂迁"],
    )
    self.assertEqual(
      [item["name"] for item in sorted(
        (item for item in items if item.get("firstNight", 0)),
        key=lambda item: item["firstNight"],
      )],
      ["化形", "疯长", "破万法", "灵视", "灵嗅", "双生花", "因果", "入梦", "夺心魄"],
    )
    self.assertTrue(all(
      item.get("firstNightReminder") if item.get("firstNight", 0) else True
      for item in items
    ))
    self.assertTrue(all(
      item.get("otherNightReminder") if item.get("otherNight", 0) else True
      for item in items
    ))

  def test_until_morale_improves_includes_board_and_traveler_cover(self):
    items = until_morale_improves()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "traveler", "fabled")],
      [13, 4, 5, 2, 5, 1],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "jinx"],
      ["解谜大师&涡流", "报丧女妖&涡流", "洗脑师&哥布林"],
    )
    self.assertIn("*建议7人以上加入旅行者", [item["text"] for item in items[0]["notes"]])

  def test_battle_of_hogwarts_uses_source_json_and_chinese_board(self):
    items = battle_of_hogwarts()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "traveler", "fabled")],
      [13, 4, 5, 4, 1, 1],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["斯莱特林挂坠盒"],
    )
    self.assertTrue(all(
      item.get("firstNightReminder") if item.get("firstNight", 0) else True
      for item in items
    ))
    self.assertTrue(all(
      item.get("otherNightReminder") if item.get("otherNight", 0) else True
      for item in items
    ))

  def test_myth_of_babylon_includes_rule_tables_and_travelers(self):
    items = myth_of_babylon()
    self.assertEqual(
      [len([item for item in items if item.get("team") == team]) for team in ("townsfolk", "outsider", "minion", "demon", "traveler", "fabled")],
      [13, 4, 4, 4, 5, 2],
    )
    self.assertEqual(
      [item["name"] for item in items if item.get("team") == "fabled"],
      ["圣洁之魂", "灯塔"],
    )
    self.assertEqual(len([item for item in items[0]["notes"] if "事”" in item["text"]]), 7)


if __name__ == "__main__":
  unittest.main()
