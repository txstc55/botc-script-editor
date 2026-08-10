#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

from audit_bilibili_scripts import (
  CatalogItem,
  LocalScript,
  OpusLink,
  bilingual_cjk_title,
  extract_script_name,
  expected_script_entries,
  is_collection_link,
  is_script_link,
  match_known_character_name,
  sync_catalog_local_artifacts,
  text_is_explained,
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

  def test_character_name_matches_middle_dot_ocr_variant(self) -> None:
    names = {"诺-达鲺", "诺·达鲺"}

    self.assertEqual(match_known_character_name("诺•达鲺", names), "诺·达鲺")

  def test_generated_image_is_refreshed_for_reused_catalog(self) -> None:
    item = CatalogItem("1", "测试", "测试", "url", "all_jsons/测试.json", "", 1, "matched", [])
    local = LocalScript(
      path="all_jsons/测试.json",
      name="测试",
      normalized_name="测试",
      exact_aliases=("测试",),
      normalized_aliases=("测试",),
      generated_image="all_jsons/测试.jpg",
    )

    self.assertEqual(sync_catalog_local_artifacts([item], [local]), 1)
    self.assertEqual(item.generated_image, "all_jsons/测试.jpg")

  def test_nested_jinx_is_included_once_in_source_order(self) -> None:
    data = [
      {"id": "a", "name": "甲", "team": "townsfolk", "ability": "甲能力", "jinxes": [
        {"id": "b", "reason": "相克原文"},
      ]},
      {"id": "b", "name": "乙", "team": "demon", "ability": "乙能力", "jinxes": [
        {"id": "a", "reason": "相克原文"},
      ]},
    ]
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "script.json"
      path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

      _, _, jinxes, _ = expected_script_entries(path)

    self.assertEqual(jinxes, [{"name": "甲&乙", "team": "jinx", "ability": "相克原文"}])

  def test_known_chinese_name_explains_bilingual_heading(self) -> None:
    self.assertTrue(text_is_explained("诡诈杰克 Knaves", ["诡诈杰克"]))


if __name__ == "__main__":
  unittest.main()
