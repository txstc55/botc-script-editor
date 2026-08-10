import unittest

from create_missing_audit_scripts import deadline_approaches, orletis_manor, taotie_feast, trial_by_ghost


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
    for items in (trial_by_ghost(), taotie_feast(), deadline_approaches()):
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


if __name__ == "__main__":
  unittest.main()
