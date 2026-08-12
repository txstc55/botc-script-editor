import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_bilibili_scripts import review_item


class ReviewOverrideTests(unittest.TestCase):
  def test_runtime_notes_are_added_without_changing_script_json(self) -> None:
    note = "中毒/醉酒：中毒的玩家会失去能力。醉酒同理。"
    with tempfile.TemporaryDirectory() as temp_dir:
      folder = Path(temp_dir)
      (folder / "对照图-01.png").write_bytes(b"board")
      script_path = folder / "整理后.json"
      original = json.dumps([
        {"id": "_meta", "name": "测试剧本"},
        {"name": "厨师", "team": "townsfolk", "ability": "测试能力"},
      ], ensure_ascii=False)
      script_path.write_text(original, encoding="utf-8")
      state_path = folder / "核对状态.json"
      state_path.write_text(json.dumps({
        "opus_id": "123",
        "source_images": ["对照图-01.png"],
      }, ensure_ascii=False), encoding="utf-8")
      lines = [
        {"text": "厨师", "x": 0.1, "y": 0.6, "height": 0.02},
        {"text": "测试能力", "x": 0.1, "y": 0.5, "height": 0.01},
      ]

      with patch("audit_bilibili_scripts.ocr_lines", return_value=lines):
        review_item(folder, Path("unused"), {
          "123": {"runtime_notes": [note], "reason": "人工逐字核对"},
        })

      state = json.loads(state_path.read_text(encoding="utf-8"))
      self.assertIn(note, [item["text"] for item in state["ocr_note_checks"]])
      self.assertEqual(original, script_path.read_text(encoding="utf-8"))

  def test_missing_json_with_only_cover_is_source_unavailable(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      folder = Path(temp_dir)
      (folder / "对照图-01.png").write_bytes(b"cover")
      state_path = folder / "核对状态.json"
      state_path.write_text(json.dumps({
        "opus_id": "123",
        "source_images": ["对照图-01.png"],
      }, ensure_ascii=False), encoding="utf-8")

      with patch("audit_bilibili_scripts.ocr_lines", return_value=[]):
        review_item(folder, Path("unused"), {})

      state = json.loads(state_path.read_text(encoding="utf-8"))
      self.assertEqual("source_unavailable", state["review_status"])

  def test_missing_json_with_reviewable_board_stays_missing(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      folder = Path(temp_dir)
      (folder / "对照图-01.png").write_bytes(b"board")
      state_path = folder / "核对状态.json"
      state_path.write_text(json.dumps({
        "opus_id": "123",
        "source_images": ["对照图-01.png"],
      }, ensure_ascii=False), encoding="utf-8")

      with patch(
        "audit_bilibili_scripts.ocr_lines",
        return_value=[{"text": str(index), "x": 0, "y": 0.5} for index in range(8)],
      ), patch(
        "audit_bilibili_scripts.detected_heading_characters",
        return_value=[str(index) for index in range(8)],
      ), patch(
        "audit_bilibili_scripts.detected_heading_character_details",
        return_value=[],
      ):
        review_item(folder, Path("unused"), {})

      state = json.loads(state_path.read_text(encoding="utf-8"))
      self.assertEqual("missing_json", state["review_status"])

  def test_source_unavailable_skips_unverifiable_ocr_issues(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      folder = Path(temp_dir)
      (folder / "对照图-01.png").write_bytes(b"cover")
      (folder / "整理后.json").write_text(json.dumps([
        {"id": "_meta", "name": "测试剧本"},
        {"name": "厨师", "team": "townsfolk", "ability": "测试能力"},
      ], ensure_ascii=False), encoding="utf-8")
      state_path = folder / "核对状态.json"
      state_path.write_text(json.dumps({
        "opus_id": "123",
        "source_images": ["对照图-01.png"],
      }, ensure_ascii=False), encoding="utf-8")

      with patch("audit_bilibili_scripts.ocr_lines", return_value=[]):
        review_item(folder, Path("unused"), {
          "123": {"source_unavailable": True, "reason": "仅封面可访问"},
        })

      state = json.loads(state_path.read_text(encoding="utf-8"))
      self.assertEqual("source_unavailable", state["review_status"])
      self.assertEqual("仅封面可访问", state["manual_verification"]["reason"])


if __name__ == "__main__":
  unittest.main()
