#!/usr/bin/env python3

import unittest

from audit_bilibili_scripts import (
  OpusLink,
  bilingual_cjk_title,
  extract_script_name,
  is_collection_link,
  is_script_link,
)


class CatalogLinkTest(unittest.TestCase):
  def test_navigation_does_not_require_collection_word(self) -> None:
    link = OpusLink("1", "【BWG剧本导航】小型剧本/特殊玩法/主题剧本")
    self.assertTrue(is_collection_link(link))

  def test_character_collection_remains_a_script(self) -> None:
    link = OpusLink("2", "【染钟楼】剧本社区—第45期《华灯初上》角色合集")
    self.assertFalse(is_collection_link(link))
    self.assertTrue(is_script_link(link))

  def test_creative_submission_is_a_script(self) -> None:
    book_title = OpusLink("3", "【染钟楼】创意投稿—第318期《激流勇进》")
    quoted_title = OpusLink("4", "【染钟楼】创意投稿—第232期“四凶降世”：剧本合集")
    self.assertTrue(is_script_link(book_title))
    self.assertTrue(is_script_link(quoted_title))
    self.assertEqual(extract_script_name(quoted_title.title), "四凶降世")

  def test_unrelated_role_post_is_not_a_script(self) -> None:
    link = OpusLink("5", "【染钟楼】角色投稿《测试角色》")
    self.assertFalse(is_script_link(link))

  def test_bilingual_title_exposes_chinese_alias(self) -> None:
    self.assertEqual(bilingual_cjk_title("天外寒情 It's Cold Outside"), "天外寒情")
    self.assertEqual(bilingual_cjk_title("The Road Not Taken 未行之路"), "未行之路")

  def test_dash_suffix_is_not_a_title_alias(self) -> None:
    self.assertEqual(bilingual_cjk_title("全员谜语人-华灯初上"), "")


if __name__ == "__main__":
  unittest.main()
