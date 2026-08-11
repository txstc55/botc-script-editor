#!/usr/bin/env python3

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from audit_bilibili_scripts import (
  CatalogItem,
  refresh_source_images,
  source_image_urls,
  source_image_urls_for_item,
  sync_local_artifacts,
)


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

  def test_new_generated_image_is_discovered_during_sync(self) -> None:
    with TemporaryDirectory() as temporary_directory:
      root = Path(temporary_directory)
      local_json = root / "script.json"
      local_json.write_text("[]\n", encoding="utf-8")
      local_image = root / "script.jpg"
      local_image.write_bytes(b"image")
      audit_folder = root / "audit"
      audit_folder.mkdir()
      metadata = {"local_json": str(local_json), "generated_image": ""}

      sync_local_artifacts(audit_folder, metadata)

      self.assertEqual(metadata["generated_image"], str(local_image))
      self.assertEqual((audit_folder / "软件生成图.jpg").read_bytes(), b"image")

  @patch("audit_bilibili_scripts.fetch_bytes", return_value=b"current")
  @patch(
    "audit_bilibili_scripts.source_image_urls_for_item",
    return_value=["https://i0.hdslb.com/bfs/new_dyn/current.png"],
  )
  def test_refresh_replaces_stale_file_for_same_image_id(self, _urls, fetch) -> None:
    with TemporaryDirectory() as temporary_directory:
      folder = Path(temporary_directory)
      image = folder / "对照图-01.png"
      image.write_bytes(b"stale")
      metadata = {
        "source_images": [image.name],
        "resolved_source_image_ids": ["current.png"],
      }

      refresh_source_images(self.item, folder, metadata)

      self.assertEqual(image.read_bytes(), b"current")
      fetch.assert_called_once()


if __name__ == "__main__":
  unittest.main()
