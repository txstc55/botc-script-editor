#!/usr/bin/env python3

import unittest
from unittest.mock import patch

from audit_bilibili_scripts import CatalogItem, source_image_urls, source_image_urls_for_item


class SourceImageTest(unittest.TestCase):
  def setUp(self) -> None:
    self.item = CatalogItem("1", "title", "name", "https://example.com/opus/1")

  @patch("audit_bilibili_scripts.jina_source_image_urls")
  @patch("audit_bilibili_scripts.source_image_urls", return_value=["direct.png"])
  @patch("audit_bilibili_scripts.fetch_opus_state", return_value={})
  def test_direct_source_is_preferred(self, _fetch, _extract, jina) -> None:
    self.assertEqual(source_image_urls_for_item(self.item), ["direct.png"])
    jina.assert_not_called()

  @patch("audit_bilibili_scripts.jina_source_image_urls", return_value=["fallback.png"])
  @patch("audit_bilibili_scripts.fetch_opus_state", side_effect=RuntimeError("blocked"))
  def test_mirror_is_fallback(self, _fetch, _jina) -> None:
    self.assertEqual(source_image_urls_for_item(self.item), ["fallback.png"])

  def test_wide_or_tall_article_images_are_kept(self) -> None:
    state = {
      "detail": {
        "modules": [{
          "module_content": {
            "wide": {"url": "https://i0.hdslb.com/bfs/new_dyn/wide.png", "width": 600, "height": 205},
            "tall": {"url": "https://i0.hdslb.com/bfs/new_dyn/tall.png", "width": 400, "height": 800},
            "small": {"url": "https://i0.hdslb.com/bfs/new_dyn/small.png", "width": 128, "height": 128},
          }
        }]
      }
    }

    self.assertEqual(source_image_urls(state), [
      "https://i0.hdslb.com/bfs/new_dyn/wide.png",
      "https://i0.hdslb.com/bfs/new_dyn/tall.png",
    ])


if __name__ == "__main__":
  unittest.main()
