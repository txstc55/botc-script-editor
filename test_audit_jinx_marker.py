#!/usr/bin/env python3

import unittest

from audit_bilibili_scripts import is_jinx_marker_line


class JinxMarkerTest(unittest.TestCase):
  def test_rule_labels_and_ocr_variants(self) -> None:
    for value in (
      "（相克规则：内容）",
      "指克規划：内容",
      "榴克规影：内容",
      "都完规：内容",
      "都烹媒：内容",
    ):
      self.assertTrue(is_jinx_marker_line(value), value)

  def test_inline_mentions_are_not_rule_labels(self) -> None:
    self.assertFalse(is_jinx_marker_line("该剧本拒不采纳新增相克规则。"))
    self.assertFalse(is_jinx_marker_line("首夜顺序规则"))


if __name__ == "__main__":
  unittest.main()
