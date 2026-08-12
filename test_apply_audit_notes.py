#!/usr/bin/env python3

import unittest
import json
import tempfile
from pathlib import Path

from apply_audit_notes import detected_notes, is_standard_note_text, process_metadata


class AuditNoteTests(unittest.TestCase):
  def test_possible_note_accepts_source_wording(self) -> None:
    notes = detected_notes([
      "某件事“可能”发生，代表说书人决定该事情是否发生。",
    ])

    self.assertEqual(len(notes), 1)
    self.assertEqual(
      notes[0]["text"],
      "可能：某件事“可能”发生，代表说书人决定该事情是否发生。",
    )

  def test_possible_note_accepts_longer_noun(self) -> None:
    notes = detected_notes([
      "某件事情“可能”发生，代表由说书人来决定该事情是否发生。",
    ])

    self.assertEqual(len(notes), 1)

  def test_process_metadata_moves_legacy_note_to_audit_status_only(self) -> None:
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      script_path = root / "script.json"
      status_path = root / "status.json"
      script = [{"id": "_meta", "name": "测试", "notes": [{"text": "特殊说明"}]}]
      script_path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
      status_path.write_text(json.dumps({
        "script_name": "测试",
        "local_json": str(script_path),
        "ocr_note_checks": [],
      }, ensure_ascii=False), encoding="utf-8")

      _, count, _ = process_metadata(status_path, True, False)

      self.assertEqual(count, 1)
      self.assertEqual(json.loads(status_path.read_text())["ocr_note_checks"], [{"text": "特殊说明"}])
      self.assertIn("notes", json.loads(script_path.read_text())[0])

  def test_standard_note_text_ignores_whitespace(self) -> None:
    self.assertTrue(is_standard_note_text("*代表：非首个夜晚"))
    self.assertTrue(is_standard_note_text("中毒：\n中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。"))
    self.assertFalse(is_standard_note_text("本剧本采用闭眼投票。"))

  def test_poison_keywords_from_unrelated_abilities_are_not_a_note(self) -> None:
    notes = detected_notes([
      "某名玩家中毒。另一名玩家失去能力。醉酒同理。",
    ])

    self.assertEqual(notes, [])

  def test_poison_note_tolerates_ocr_errors_in_player(self) -> None:
    notes = detected_notes([
      "中毒的玩案会失去能力，但会认为自己仍具有能力。",
      "如果中毒玩象的角色能力会给他提供信息，说书人可能会给出错误信息，",
      "中毒的玩家不会得知自己中毒。",
    ])

    self.assertEqual([note["text"].split("：", 1)[0] for note in notes], ["中毒"])

  def test_poison_drunk_note_tolerates_ocr_error_in_drunk(self) -> None:
    notes = detected_notes([
      "中毒的玩案会失去能力。如果中毒玩家的能力提供信息，可能会得到错误信息。",
      "中毒的玩家不会得知自己中毒。辞酒同理。",
    ])

    self.assertEqual([note["text"].split("：", 1)[0] for note in notes], ["中毒/醉酒"])


if __name__ == "__main__":
  unittest.main()
