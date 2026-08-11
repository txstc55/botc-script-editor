import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_bilibili_scripts import review_item


class ReviewOverrideTests(unittest.TestCase):
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
