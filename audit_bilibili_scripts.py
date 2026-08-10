#!/usr/bin/env python3
"""Collect Bilibili script posts and prepare per-script comparison folders."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


ROOT_URL = "https://www.bilibili.com/opus/882589412561518648"
JINA_OPUS_URL = "https://r.jina.ai/http://www.bilibili.com/opus/{opus_id}"
USER_AGENT = (
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
)
INITIAL_STATE_MARKER = "window.__INITIAL_STATE__="
OPUS_RE = re.compile(r"/opus/(\d+)")
SCRIPT_NAME_RE = re.compile(r"《([^》]+)》|“([^”]+)”")
VERSION_RE = re.compile(r"(?i)(?:[-_ ]?(?:v(?:er(?:sion)?)?\s*)?\d+(?:\.\d+)*)$")
LEADING_FILE_NUMBER_RE = re.compile(r"^\s*\d*#\s*")
PARENTHETICAL_RE = re.compile(r"[（(][^）)]*[）)]")
CJK_TITLE_RE = re.compile(r"[\u3400-\u9fff\U00020000-\U0003134f]{3,}")
PAGE_FETCH_LOCK = threading.Lock()
PAGE_FETCH_INTERVAL = 1.25
page_fetch_not_before = 0.0
JINA_FETCH_LOCK = threading.Lock()
JINA_FETCH_INTERVAL = 1.25
jina_fetch_not_before = 0.0


@dataclass(frozen=True)
class OpusLink:
  id: str
  title: str

  @property
  def url(self) -> str:
    return f"https://www.bilibili.com/opus/{self.id}"


@dataclass(frozen=True)
class LocalScript:
  path: str
  name: str
  normalized_name: str
  exact_aliases: tuple[str, ...]
  normalized_aliases: tuple[str, ...]
  generated_image: str


@dataclass
class CatalogItem:
  opus_id: str
  title: str
  script_name: str
  url: str
  local_json: str = ""
  generated_image: str = ""
  match_score: float = 0.0
  status: str = "unmatched"
  source_image_ids: list[str] = field(default_factory=list)


class OpusLinkParser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self._active_id = ""
    self._active_text: list[str] = []
    self.links: list[OpusLink] = []

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    if tag != "a" or self._active_id:
      return
    href = dict(attrs).get("href") or ""
    match = OPUS_RE.search(href)
    if match:
      self._active_id = match.group(1)
      self._active_text = []

  def handle_data(self, data: str) -> None:
    if self._active_id:
      self._active_text.append(data)

  def handle_endtag(self, tag: str) -> None:
    if tag != "a" or not self._active_id:
      return
    title = clean_space("".join(self._active_text))
    if title:
      self.links.append(OpusLink(self._active_id, title))
    self._active_id = ""
    self._active_text = []


def clean_space(value: Any) -> str:
  return re.sub(r"\s+", " ", str(value or "")).strip()


def is_jinx_marker_line(value: Any) -> bool:
  text = clean_space(value).lstrip("（(")
  head = re.split(r"[：:]", text, maxsplit=1)[0]
  normalized = head.translate(str.maketrans({
    "規": "规",
    "則": "则",
    "劇": "则",
    "剧": "则",
  }))
  if "顺序规则" in normalized:
    return False
  return bool(re.match(r"^[相指榴都][克完烹][规媒].{0,1}[则影期划]?", normalized))


def is_reference_webpage_screenshot(value: Any) -> bool:
  text = clean_space(value)
  return (
    "游戏信息" in text
    and "规则概要" in text
    and "角色能力" in text
    and "总览" in text
  )


def fetch_bytes(url: str, retries: int = 3) -> bytes:
  request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": ROOT_URL})
  for attempt in range(retries):
    try:
      with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()
    except (urllib.error.URLError, TimeoutError):
      if attempt + 1 == retries:
        raise
      time.sleep(1.5 * (attempt + 1))
  raise RuntimeError(f"无法下载：{url}")


def fetch_html(url: str) -> str:
  return fetch_bytes(url).decode("utf-8", errors="replace")


def parse_initial_state(html: str) -> dict[str, Any]:
  marker_index = html.find(INITIAL_STATE_MARKER)
  if marker_index < 0:
    raise ValueError("页面中没有 window.__INITIAL_STATE__")
  start = marker_index + len(INITIAL_STATE_MARKER)
  state, _ = json.JSONDecoder().raw_decode(html[start:])
  if not isinstance(state, dict):
    raise ValueError("Bilibili 页面状态不是对象")
  return state


def fetch_opus_state(url: str, retries: int = 6) -> dict[str, Any]:
  global page_fetch_not_before
  last_error: Exception | None = None
  for attempt in range(retries):
    with PAGE_FETCH_LOCK:
      delay = page_fetch_not_before - time.monotonic()
      if delay > 0:
        time.sleep(delay)
      html = fetch_html(url)
      page_fetch_not_before = time.monotonic() + PAGE_FETCH_INTERVAL
    try:
      return parse_initial_state(html)
    except ValueError as error:
      last_error = error
      cooldown = min(120.0, 10.0 * (2 ** attempt))
      with PAGE_FETCH_LOCK:
        page_fetch_not_before = max(page_fetch_not_before, time.monotonic() + cooldown)
  raise RuntimeError(f"Bilibili 页面持续返回风控内容：{last_error}")


def extract_links(html: str) -> list[OpusLink]:
  parser = OpusLinkParser()
  parser.feed(html)
  best_by_id: dict[str, OpusLink] = {}
  for link in parser.links:
    current = best_by_id.get(link.id)
    if not current or len(link.title) > len(current.title):
      best_by_id[link.id] = link
  return list(best_by_id.values())


def is_collection_link(link: OpusLink) -> bool:
  return "【BWG剧本导航】" in link.title


def is_script_link(link: OpusLink) -> bool:
  return (
    any(kind in link.title for kind in ("剧本社区", "创意投稿"))
    and bool(SCRIPT_NAME_RE.search(link.title))
  )


def extract_script_name(title: str) -> str:
  match = SCRIPT_NAME_RE.search(title)
  if not match:
    return clean_space(title)
  return clean_space(next(group for group in match.groups() if group))


def normalize_script_name(value: str, strip_version: bool = True) -> str:
  normalized = unicodedata.normalize("NFKC", clean_space(value))
  normalized = normalized.strip("#《》【】[]()（）·—-_")
  if strip_version:
    normalized = VERSION_RE.sub("", normalized)
  return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", normalized).lower()


def meta_name(data: Any, fallback: str) -> str:
  if isinstance(data, list):
    for item in data:
      if isinstance(item, dict) and str(item.get("id", "")).strip() == "_meta":
        return clean_space(item.get("name")) or fallback
  if isinstance(data, dict):
    return clean_space(data.get("name")) or fallback
  return fallback


def generated_image_for_json(path: Path) -> str:
  for suffix in (".jpg", ".jpeg", ".png"):
    candidate = path.with_suffix(suffix)
    if candidate.exists():
      return str(candidate)
  return ""


def local_script_names(path: Path, meta_script_name: str) -> list[str]:
  stem = unicodedata.normalize("NFKC", path.stem)
  stem = LEADING_FILE_NUMBER_RE.sub("", stem).strip()
  without_author = stem.rsplit("-", 1)[0].strip() if "-" in stem else stem
  without_parenthetical = PARENTHETICAL_RE.sub("", without_author).strip()
  names = [meta_script_name, stem, without_author, without_parenthetical]
  for name in list(names):
    cjk_title = bilingual_cjk_title(name)
    if cjk_title:
      names.append(cjk_title)
  return list(dict.fromkeys(name for name in names if clean_space(name)))


def bilingual_cjk_title(value: str) -> str:
  """Return the Chinese title from a bilingual title, not a subtitle after a dash."""
  text = clean_space(value).lstrip("#《【")
  leading = CJK_TITLE_RE.match(text)
  if leading:
    rest = text[leading.end():].lstrip()
    return leading.group() if rest and rest[0].isascii() and rest[0].isalpha() else ""
  if not text or not text[0].isascii() or not text[0].isalpha():
    return ""
  matches = list(CJK_TITLE_RE.finditer(text))
  if len(matches) != 1:
    return ""
  return matches[0].group()


def load_local_scripts(root: Path) -> list[LocalScript]:
  scripts: list[LocalScript] = []
  for path in sorted(root.rglob("*.json")):
    try:
      data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      continue
    name = meta_name(data, path.stem)
    aliases = local_script_names(path, name)
    scripts.append(LocalScript(
      path=str(path),
      name=name,
      normalized_name=normalize_script_name(name),
      exact_aliases=tuple(dict.fromkeys(
        normalize_script_name(alias, strip_version=False) for alias in aliases
      )),
      normalized_aliases=tuple(dict.fromkeys(
        normalize_script_name(alias) for alias in aliases
      )),
      generated_image=generated_image_for_json(path),
    ))
  return scripts


def best_local_match(script_name: str, local_scripts: list[LocalScript]) -> tuple[LocalScript | None, float]:
  exact = normalize_script_name(script_name, strip_version=False)
  normalized = normalize_script_name(script_name)
  exact_matches = [
    item for item in local_scripts
    if exact in item.exact_aliases
  ]
  if exact_matches:
    return preferred_duplicate(script_name, exact_matches), 1.0

  normalized_matches = [item for item in local_scripts if normalized in item.normalized_aliases]
  if normalized_matches:
    return preferred_duplicate(script_name, normalized_matches), 0.99

  candidates = exact_matches or normalized_matches or local_scripts
  scored = sorted([
    (
      max(
        SequenceMatcher(None, normalized, alias).ratio()
        for alias in item.normalized_aliases
      ),
      item,
    )
    for item in candidates
  ], key=lambda value: (value[0], value[1].path))
  if not scored or scored[-1][0] < 0.9:
    return None, scored[-1][0] if scored else 0.0
  best_score, best = scored[-1]
  if len(scored) > 1 and best_score - scored[-2][0] < 0.03:
    return None, best_score
  return best, best_score


def preferred_duplicate(script_name: str, candidates: list[LocalScript]) -> LocalScript:
  target = normalize_script_name(script_name, strip_version=False)
  return max(candidates, key=lambda item: (
    bool(item.generated_image),
    max(SequenceMatcher(None, target, alias).ratio() for alias in item.exact_aliases),
    -len(Path(item.path).parts),
    item.path,
  ))


def collect_catalog(root_url: str, local_scripts: list[LocalScript]) -> list[CatalogItem]:
  root_html = fetch_html(root_url)
  pending = [link for link in extract_links(root_html) if is_collection_link(link)]
  root_match = OPUS_RE.search(root_url)
  seen_collections = {root_match.group(1)} if root_match else set()
  scripts_by_id: dict[str, OpusLink] = {
    link.id: link for link in extract_links(root_html) if is_script_link(link)
  }

  while pending:
    collection = pending.pop(0)
    if collection.id in seen_collections:
      continue
    seen_collections.add(collection.id)
    html = fetch_html(collection.url)
    for link in extract_links(html):
      if is_collection_link(link) and link.id not in seen_collections:
        pending.append(link)
      if is_script_link(link):
        scripts_by_id.setdefault(link.id, link)
    time.sleep(0.15)

  catalog: list[CatalogItem] = []
  for link in sorted(scripts_by_id.values(), key=lambda item: int(item.id)):
    script_name = extract_script_name(link.title)
    local, score = best_local_match(script_name, local_scripts)
    catalog.append(CatalogItem(
      opus_id=link.id,
      title=link.title,
      script_name=script_name,
      url=link.url,
      local_json=local.path if local else "",
      generated_image=local.generated_image if local else "",
      match_score=round(score, 4),
      status="matched" if local else "unmatched",
    ))
  return catalog


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
  if isinstance(value, dict):
    yield value
    for child in value.values():
      yield from walk_dicts(child)
  elif isinstance(value, list):
    for child in value:
      yield from walk_dicts(child)


def source_image_urls(state: dict[str, Any]) -> list[str]:
  detail = state.get("detail")
  modules = detail.get("modules", []) if isinstance(detail, dict) else []
  urls: list[str] = []
  for module in modules:
    if not isinstance(module, dict) or not module.get("module_content"):
      continue
    for record in walk_dicts(module["module_content"]):
      url = record.get("url")
      width = record.get("width", 0)
      height = record.get("height", 0)
      if not isinstance(url, str) or "hdslb.com/bfs/" not in url:
        continue
      if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        continue
      if width < 600 or height < 600 or url in urls:
        continue
      urls.append(url)
  return urls


def jina_source_image_urls(opus_id: str) -> list[str]:
  global jina_fetch_not_before
  with JINA_FETCH_LOCK:
    delay = jina_fetch_not_before - time.monotonic()
    if delay > 0:
      time.sleep(delay)
    jina_fetch_not_before = time.monotonic() + JINA_FETCH_INTERVAL
  markdown = fetch_bytes(
    JINA_OPUS_URL.format(opus_id=opus_id),
    retries=6,
  ).decode("utf-8", errors="replace")
  urls: list[str] = []
  for raw_url in re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", markdown):
    if "hdslb.com/bfs/" not in raw_url or "/face/" in raw_url:
      continue
    width_match = re.search(r"@(\d+)w", raw_url)
    if width_match and int(width_match.group(1)) < 600:
      continue
    original_url = raw_url.split("@", 1)[0].replace("http://", "https://", 1)
    if original_url not in urls:
      urls.append(original_url)
  if not urls:
    raise RuntimeError("正文镜像中没有找到大型 Bilibili 图片")
  return urls


def source_image_urls_for_item(item: CatalogItem) -> list[str]:
  try:
    urls = source_image_urls(fetch_opus_state(item.url, retries=2))
    if not urls:
      raise RuntimeError("页面状态中没有找到大型 Bilibili 图片")
  except Exception as bilibili_error:
    try:
      urls = jina_source_image_urls(item.opus_id)
    except Exception as jina_error:
      raise RuntimeError(f"Bilibili 直连失败：{bilibili_error}；正文镜像失败：{jina_error}") from jina_error
  if not item.source_image_ids:
    return urls
  selected_ids = set(item.source_image_ids)
  selected = [url for url in urls if source_image_id(url) in selected_ids]
  missing_ids = selected_ids - {source_image_id(url) for url in selected}
  if missing_ids:
    raise RuntimeError(f"人工指定的原图不存在：{', '.join(sorted(missing_ids))}")
  return selected


def source_image_id(url: str) -> str:
  return Path(urlparse(url.split("@", 1)[0]).path).name


def safe_name(value: str) -> str:
  value = re.sub(r"[\\/:*?\"<>|]", "_", clean_space(value))
  return value[:100].rstrip(". ") or "未命名剧本"


def image_suffix(url: str) -> str:
  suffix = Path(url.split("?", 1)[0]).suffix.lower()
  return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".png"


def copy_if_present(source: str, destination: Path) -> None:
  if source and Path(source).exists():
    shutil.copy2(source, destination)


def sync_local_artifacts(folder: Path, metadata: dict[str, Any]) -> None:
  local_json = clean_space(metadata.get("local_json"))
  generated_image = clean_space(metadata.get("generated_image"))
  if local_json:
    copy_if_present(local_json, folder / "整理后.json")
  else:
    (folder / "整理后.json").unlink(missing_ok=True)
  if generated_image:
    copy_if_present(
      generated_image,
      folder / f"软件生成图{Path(generated_image).suffix.lower()}",
    )
  else:
    for stale_image in folder.glob("软件生成图.*"):
      stale_image.unlink()


def refresh_source_images(item: CatalogItem, folder: Path, metadata: dict[str, Any]) -> None:
  urls = source_image_urls_for_item(item)
  old_files = [
    clean_space(value) for value in metadata.get("source_images", [])
    if clean_space(value)
  ]
  old_ids = [
    clean_space(value) for value in metadata.get("resolved_source_image_ids", [])
    if clean_space(value)
  ]
  source_files: list[str] = []
  resolved_ids: list[str] = []
  downloaded_ids: list[str] = []
  for index, url in enumerate(urls, start=1):
    image_id = source_image_id(url)
    destination = folder / f"对照图-{index:02d}{image_suffix(url)}"
    old_path = folder / old_files[index - 1] if index <= len(old_files) else None
    can_reuse = bool(
      old_path and old_path.exists() and (
        not old_ids or (index <= len(old_ids) and old_ids[index - 1] == image_id)
      )
    )
    if can_reuse:
      destination = old_path
    else:
      destination.write_bytes(fetch_bytes(url))
      downloaded_ids.append(image_id)
    source_files.append(destination.name)
    resolved_ids.append(image_id)

  for old_file in set(old_files) - set(source_files):
    (folder / old_file).unlink(missing_ok=True)
  metadata["source_images"] = source_files
  metadata["resolved_source_image_ids"] = resolved_ids
  if downloaded_ids:
    metadata["source_image_added_ids"] = list(dict.fromkeys([
      *metadata.get("source_image_added_ids", []),
      *downloaded_ids,
    ]))


def prepare_item(
  item: CatalogItem,
  output_root: Path,
  refresh: bool = False,
  refresh_sources: bool = False,
) -> Path:
  folder = output_root / "剧本" / f"{safe_name(item.script_name)}-{item.opus_id}"
  folder.mkdir(parents=True, exist_ok=True)
  metadata_path = folder / "核对状态.json"
  if metadata_path.exists() and not refresh:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(asdict(item))
    if refresh_sources:
      refresh_source_images(item, folder, metadata)
    metadata_path.write_text(
      json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
      encoding="utf-8",
    )
    sync_local_artifacts(folder, metadata)
    return folder

  images = source_image_urls_for_item(item)
  source_files: list[str] = []
  for index, url in enumerate(images, start=1):
    destination = folder / f"对照图-{index:02d}{image_suffix(url)}"
    if refresh or not destination.exists():
      destination.write_bytes(fetch_bytes(url))
    source_files.append(destination.name)

  if item.local_json:
    copy_if_present(item.local_json, folder / "整理后.json")
  if item.generated_image:
    copy_if_present(item.generated_image, folder / f"软件生成图{Path(item.generated_image).suffix.lower()}")

  metadata = {
    **asdict(item),
    "source_images": source_files,
    "resolved_source_image_ids": [source_image_id(url) for url in images],
    "review_status": "pending",
    "review_notes": [],
  }
  metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  return folder


def build_ocr_tool(output_root: Path) -> Path:
  source = Path(__file__).with_name("ocr_script_image.swift")
  tools_dir = output_root / "_tools"
  tools_dir.mkdir(parents=True, exist_ok=True)
  binary = tools_dir / "script-ocr"
  if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
    subprocess.run(["swiftc", "-O", str(source), "-o", str(binary)], check=True)
  return binary


def ocr_lines(binary: Path, image: Path) -> list[dict[str, Any]]:
  result = subprocess.run(
    [str(binary), str(image)],
    check=True,
    capture_output=True,
    text=True,
  )
  value = json.loads(result.stdout)
  return value if isinstance(value, list) else []


def json_items(data: Any) -> list[dict[str, Any]]:
  if isinstance(data, list):
    return [item for item in data if isinstance(item, dict)]
  if isinstance(data, dict):
    for key in ("characters", "script", "roles", "items", "data"):
      value = data.get(key)
      if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
  return []


def expected_script_entries(
  json_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[str]]:
  data = json.loads(json_path.read_text(encoding="utf-8"))
  items = json_items(data)
  names_by_id = {
    clean_space(item.get("id")): clean_space(item.get("name"))
    for item in items
    if clean_space(item.get("id")) and clean_space(item.get("name"))
  }
  required: list[dict[str, str]] = []
  travelers: list[dict[str, str]] = []
  jinxes: list[dict[str, str]] = []
  notes: list[str] = []
  nested_reasons: set[str] = set()
  for item in items:
    if clean_space(item.get("id")) == "_meta":
      for note in item.get("notes", []):
        if isinstance(note, dict):
          text = clean_space(note.get("text"))
        else:
          text = clean_space(note)
        if text:
          notes.append(text)
      continue
    team = clean_space(item.get("team")).lower()
    name = clean_space(item.get("name"))
    if not name:
      continue
    entry = {
      "name": name,
      "team": team,
      "ability": clean_space(item.get("ability")),
    }
    if "jinx" in team:
      jinxes.append(entry)
      continue
    if team in {"traveler", "travelers", "traveller", "traveller2"}:
      travelers.append(entry)
    else:
      required.append(entry)
    for nested in item.get("jinxes", []):
      if not isinstance(nested, dict):
        continue
      reason = clean_space(nested.get("reason") or nested.get("ability"))
      target = names_by_id.get(clean_space(nested.get("id")), clean_space(nested.get("name")))
      if not reason or not target or reason in nested_reasons:
        continue
      nested_reasons.add(reason)
      jinxes.append({
        "name": f"{name}&{target}",
        "team": "jinx",
        "ability": reason,
      })
  return required, travelers, jinxes, notes


def normalized_ocr_text(value: str) -> str:
  value = unicodedata.normalize("NFKC", value)
  value = re.sub(r"<[^>]+>", "", value)
  return re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", "", value).lower()


def ngram_coverage(expected: str, actual: str, size: int = 3) -> float:
  expected_text = normalized_ocr_text(expected)
  actual_text = normalized_ocr_text(actual)
  if not expected_text:
    return 1.0
  gram_size = min(size, len(expected_text))
  grams = [
    expected_text[index:index + gram_size]
    for index in range(len(expected_text) - gram_size + 1)
  ]
  return sum(gram in actual_text for gram in grams) / len(grams)


def content_checks(entries: list[dict[str, str]], ocr_text: str) -> list[dict[str, Any]]:
  return [
    {
      "name": entry["name"],
      "team": entry["team"],
      "ability_coverage": round(ngram_coverage(entry["ability"], ocr_text), 4),
    }
    for entry in entries
  ]


@lru_cache(maxsize=1)
def known_character_teams() -> dict[str, set[str]]:
  database_root = Path(__file__).with_name("script_editor") / "public" / "characters"
  folder_teams = {
    "townsfolks": "townsfolk",
    "outsiders": "outsider",
    "minions": "minion",
    "demons": "demon",
    "travelers": "traveler",
    "fabled": "fabled",
  }
  teams_by_name: dict[str, set[str]] = defaultdict(set)
  for index_path in database_root.glob("*/index.json"):
    try:
      index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
      continue
    for item in index.get("characters", []):
      if isinstance(item, dict):
        name = clean_space(item.get("name"))
        if name:
          team = folder_teams.get(index_path.parent.name, "")
          if team:
            teams_by_name[name].add(team)
  return teams_by_name


@lru_cache(maxsize=1)
def known_character_names() -> set[str]:
  return set(known_character_teams())


def match_known_character_name(value: Any, known_names: set[str]) -> str:
  text = clean_space(value)
  if normalized_ocr_text(text) in {"疯狂", "中毒", "醉酒", "中毒醉酒", "可能", "代表非首个夜晚"}:
    return ""
  if text in known_names:
    return text
  normalized = normalized_ocr_text(text)
  candidates = [name for name in known_names if normalized_ocr_text(name) == normalized]
  if not candidates:
    return ""
  comparable = text.replace("•", "·").replace("‧", "·")
  return max(candidates, key=lambda name: (SequenceMatcher(None, comparable, name).ratio(), name))


def detected_heading_characters(lines: list[dict[str, Any]]) -> list[str]:
  known_names = known_character_names()
  detected: list[str] = []
  for line in lines:
    text = match_known_character_name(line.get("text"), known_names)
    height = float(line.get("height", 0))
    if height >= 0.012 and text and text not in detected:
      detected.append(text)
  return detected


def section_team(text: str) -> str:
  normalized = normalized_ocr_text(text)
  if normalized.startswith(("善良阵营", "邪恶阵营")):
    for label, team in (
      ("外来者", "outsider"),
      ("镇民", "townsfolk"),
      ("爪牙", "minion"),
      ("恶魔", "demon"),
    ):
      if label in normalized:
        return team
  if normalized.startswith(("传奇角色", "奇遇角色")):
    return "fabled"
  if normalized.startswith("剧本旅行者") or normalized == "旅行者":
    return "traveler"
  return ""


def detected_heading_character_details(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
  known_names = known_character_names()
  teams_by_name = known_character_teams()
  markers = sorted([
    {
      "team": team,
      "y": float(line.get("y", 0)),
    }
    for line in lines
    if (team := section_team(clean_space(line.get("text"))))
  ], key=lambda marker: -marker["y"])
  details: list[dict[str, Any]] = []
  seen: set[tuple[str, str]] = set()
  for line in sorted(lines, key=lambda value: (-float(value.get("y", 0)), float(value.get("x", 0)))):
    name = match_known_character_name(line.get("text"), known_names)
    x = float(line.get("x", 0))
    if not name or float(line.get("height", 0)) < 0.012 or x > 0.85:
      continue
    y = float(line.get("y", 0))
    marker = next((item for item in reversed(markers) if item["y"] > y), None)
    team = marker["team"] if marker else ""
    known_teams = teams_by_name.get(name, set())
    if team not in known_teams and len(known_teams) == 1:
      team = next(iter(known_teams))
    elif team not in known_teams:
      team = ""
    identity = (name, team)
    if identity in seen:
      continue
    seen.add(identity)
    details.append({
      "name": name,
      "team": team,
      "x": round(x, 5),
      "y": round(y, 5),
    })
  return details


def group_source_boards(source_reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
  groups: list[dict[str, Any]] = []
  for review in source_reviews:
    characters = set(review.get("heading_characters", []))
    if len(characters) < 8:
      continue
    matched_group: dict[str, Any] | None = None
    for group in groups:
      group_characters = set(group["characters"])
      union = characters | group_characters
      similarity = len(characters & group_characters) / len(union) if union else 1.0
      if similarity >= 0.7:
        matched_group = group
        break
    if matched_group:
      matched_group["images"].append(review["image"])
      matched_group["characters"] = sorted(set(matched_group["characters"]) | characters)
    else:
      groups.append({
        "images": [review["image"]],
        "characters": sorted(characters),
      })
  return groups


def text_is_explained(text: str, known_texts: list[str]) -> bool:
  normalized = normalized_ocr_text(text)
  if len(normalized) < 4:
    return True
  return any(
    normalized in normalized_ocr_text(known)
    or (
      len(normalized_ocr_text(known)) >= 3
      and normalized_ocr_text(known) in normalized
    )
    or ngram_coverage(text, known) >= 0.6
    or SequenceMatcher(None, normalized, normalized_ocr_text(known)).ratio() >= 0.7
    for known in known_texts
    if known
  )


def review_item(
  folder: Path,
  ocr_binary: Path,
  review_overrides: dict[str, Any] | None = None,
) -> None:
  metadata_path = folder / "核对状态.json"
  json_path = folder / "整理后.json"
  if not metadata_path.exists():
    return
  metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
  if not json_path.exists():
    candidates: list[tuple[int, int, Path, list[str]]] = []
    source_reviews: list[dict[str, Any]] = []
    for file_name in metadata.get("source_images", []):
      image = folder / file_name
      lines = ocr_lines(ocr_binary, image)
      heading_names = detected_heading_characters(lines)
      candidates.append((len(heading_names), image.stat().st_size, image, heading_names))
      source_reviews.append({
        "image": image.name,
        "heading_characters": heading_names,
        "heading_character_details": detected_heading_character_details(lines),
      })
    source_board_groups = group_source_boards(source_reviews)
    metadata.update({
      "ocr_source_images": source_reviews,
      "ocr_source_board_groups": source_board_groups,
    })
    if not candidates:
      metadata["review_status"] = "no_source_image"
    else:
      _, _, image, heading_names = max(candidates, key=lambda value: (value[0], value[1]))
      metadata.update({
        "review_status": "missing_json",
        "ocr_reference_image": image.name,
        "ocr_heading_characters": heading_names,
        "ocr_heading_character_details": next(
          review["heading_character_details"]
          for review in source_reviews if review["image"] == image.name
        ),
      })
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return
  required, travelers, jinxes, notes = expected_script_entries(json_path)
  required_names = [entry["name"] for entry in required]
  candidates: list[tuple[int, int, Path, list[dict[str, Any]], str]] = []
  source_reviews: list[dict[str, Any]] = []
  for file_name in metadata.get("source_images", []):
    image = folder / file_name
    lines = ocr_lines(ocr_binary, image)
    text = "\n".join(clean_space(line.get("text")) for line in lines)
    score = sum(name in text for name in required_names)
    candidates.append((score, image.stat().st_size, image, lines, text))
    source_reviews.append({
      "image": image.name,
      "heading_characters": detected_heading_characters(lines),
      "heading_character_details": detected_heading_character_details(lines),
      "required_character_matches": score,
    })
  if not candidates:
    metadata["review_status"] = "no_source_image"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return

  reference_candidate = max(candidates, key=lambda value: (value[0], value[1]))
  score, _, image, lines, text = reference_candidate
  board_candidates = [reference_candidate]
  for candidate in candidates:
    if candidate is reference_candidate:
      continue
    if is_reference_webpage_screenshot(candidate[4]):
      continue
    heading_count = len(detected_heading_characters(candidate[3]))
    has_supplemental_content = any(marker in candidate[4] for marker in (
      "相克规则", "传奇角色", "剧本旅行者", "私货商人", "中毒", "醉酒", "可能",
    ))
    if heading_count < 8 and has_supplemental_content:
      board_candidates.append(candidate)
  board_text = "\n".join(
    candidate[4] for candidate in board_candidates
  )
  board_lines = [
    line
    for candidate in board_candidates
    for line in candidate[3]
  ]
  exact_missing = [name for name in required_names if name not in board_text]
  visible_travelers = [entry for entry in travelers if entry["name"] in board_text]
  traveler_hits = [entry["name"] for entry in visible_travelers]
  ability_checks = content_checks(required, board_text)
  traveler_checks = content_checks(visible_travelers, board_text)
  jinx_checks = content_checks(jinxes, board_text)
  note_checks = [
    {
      "text": note,
      "text_coverage": round(ngram_coverage(note, board_text), 4),
    }
    for note in notes
  ]
  ability_coverage_by_name = {
    check["name"]: check["ability_coverage"] for check in ability_checks
  }
  name_confirmed_by_ability = [
    name for name in exact_missing
    if ability_coverage_by_name.get(name, 0.0) >= 0.65
  ]
  missing = [name for name in exact_missing if name not in name_confirmed_by_ability]
  score = len(required_names) - len(missing)
  ability_mismatches = [
    check["name"] for check in ability_checks
    if check["ability_coverage"] < 0.45
  ]
  traveler_mismatches = [
    check["name"] for check in traveler_checks
    if check["ability_coverage"] < 0.45
  ]
  jinx_mismatches = [
    check["name"] for check in jinx_checks
    if check["ability_coverage"] < 0.35
  ]
  jinx_marker_count = sum(is_jinx_marker_line(line.get("text")) for line in board_lines)
  missing_jinx_rule_count = max(0, jinx_marker_count - len(jinxes))
  note_mismatches = [
    check["text"] for check in note_checks
    if check["text_coverage"] < 0.45
  ]
  expected_name_set = {
    entry["name"] for entry in [*required, *travelers]
  }
  heading_character_details = detected_heading_character_details(lines)
  heading_characters = list(dict.fromkeys(
    item["name"] for item in heading_character_details if item.get("team")
  ))
  unexpected_characters = [
    name for name in heading_characters if name not in expected_name_set
  ]
  bottom_lines = [
    clean_space(line.get("text"))
    for line in sorted(lines, key=lambda line: -float(line.get("y", 0)))
    if float(line.get("y", 0)) < 0.17 and clean_space(line.get("text"))
  ]
  known_texts = [
    value
    for entry in [*required, *visible_travelers, *jinxes]
    for value in (entry["name"], entry["ability"])
  ] + notes + [
    "善良阵营镇民",
    "善良阵营外来者",
    "邪恶阵营爪牙",
    "邪恶阵营恶魔",
    "剧本旅行者",
    "传奇角色",
    "奇遇角色",
    "传奇角色说书人",
  ]
  unexplained_bottom_lines = [
    line for line in bottom_lines
    if not text_is_explained(line, known_texts)
  ]
  rule_markers = [
    marker for marker in ("私货商人", "剧本规则", "特殊规则", "相克规则")
    if marker in board_text
  ]
  missing_rule_data = bool(rule_markers and not any(
    entry["team"] == "fabled" for entry in required
  ) and not jinxes and not notes)
  raw_issues = {
    "ability_mismatches": ability_mismatches,
    "traveler_mismatches": traveler_mismatches,
    "jinx_mismatches": jinx_mismatches,
    "note_mismatches": note_mismatches,
    "unexplained_bottom_lines": unexplained_bottom_lines,
  }
  manual = (review_overrides or {}).get(str(metadata.get("opus_id", "")), {})
  if not isinstance(manual, dict):
    raise ValueError("人工核对表条目必须是对象")
  verified = {
    "ability_mismatches": set(manual.get("verified_abilities", [])),
    "traveler_mismatches": set(manual.get("verified_travelers", [])),
    "jinx_mismatches": set(manual.get("verified_jinxes", [])),
    "note_mismatches": set(manual.get("verified_notes", [])),
    "unexplained_bottom_lines": set(manual.get("verified_bottom_lines", [])),
  }
  ability_mismatches = [value for value in ability_mismatches if value not in verified["ability_mismatches"]]
  traveler_mismatches = [value for value in traveler_mismatches if value not in verified["traveler_mismatches"]]
  jinx_mismatches = [value for value in jinx_mismatches if value not in verified["jinx_mismatches"]]
  note_mismatches = [value for value in note_mismatches if value not in verified["note_mismatches"]]
  unexplained_bottom_lines = [
    value for value in unexplained_bottom_lines
    if value not in verified["unexplained_bottom_lines"]
  ]
  has_manual_verification = any(
    set(values) & verified[key] for key, values in raw_issues.items()
  )
  needs_manual_review = bool(
    missing or ability_mismatches or traveler_mismatches or jinx_mismatches or note_mismatches or
    unexplained_bottom_lines or missing_rule_data or unexpected_characters or missing_jinx_rule_count
  )
  metadata.update({
    "review_status": (
      "needs_manual_review" if needs_manual_review
      else "manual_content_match" if has_manual_verification
      else "ocr_content_match"
    ),
    "manual_verification": manual if has_manual_verification else {},
    "ocr_raw_issues": raw_issues,
    "ocr_reference_image": image.name,
    "ocr_character_matches": score,
    "ocr_required_character_count": len(required_names),
    "ocr_missing_characters": missing,
    "ocr_name_confirmed_by_ability": name_confirmed_by_ability,
    "ocr_heading_characters": heading_characters,
    "ocr_heading_character_details": heading_character_details,
    "ocr_unexpected_characters": unexpected_characters,
    "ocr_travelers_seen": traveler_hits,
    "ocr_ability_checks": ability_checks,
    "ocr_ability_mismatches": ability_mismatches,
    "ocr_traveler_checks": traveler_checks,
    "ocr_traveler_mismatches": traveler_mismatches,
    "ocr_jinx_checks": jinx_checks,
    "ocr_jinx_mismatches": jinx_mismatches,
    "ocr_jinx_marker_count": jinx_marker_count,
    "ocr_missing_jinx_rule_count": missing_jinx_rule_count,
    "ocr_note_checks": note_checks,
    "ocr_note_mismatches": note_mismatches,
    "ocr_bottom_text": bottom_lines,
    "ocr_unexplained_bottom_lines": unexplained_bottom_lines,
    "ocr_rule_markers": rule_markers,
    "ocr_missing_rule_data": missing_rule_data,
    "ocr_source_images": source_reviews,
    "ocr_source_board_groups": group_source_boards(source_reviews),
  })
  metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_catalog(catalog: list[CatalogItem], output_root: Path) -> None:
  output_root.mkdir(parents=True, exist_ok=True)
  payload = {
    "source": ROOT_URL,
    "total": len(catalog),
    "matched": sum(item.status == "matched" for item in catalog),
    "unmatched": sum(item.status != "matched" for item in catalog),
    "items": [asdict(item) for item in catalog],
  }
  (output_root / "剧本清单.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )


def read_catalog(path: Path) -> list[CatalogItem]:
  payload = json.loads(path.read_text(encoding="utf-8"))
  raw_items = payload.get("items", []) if isinstance(payload, dict) else []
  return [
    CatalogItem(
      opus_id=str(item.get("opus_id", "")),
      title=str(item.get("title", "")),
      script_name=str(item.get("script_name", "")),
      url=str(item.get("url", "")),
      local_json=str(item.get("local_json", "")),
      generated_image=str(item.get("generated_image", "")),
      match_score=float(item.get("match_score", 0.0) or 0.0),
      status=str(item.get("status", "unmatched")),
      source_image_ids=[
        str(value) for value in item.get("source_image_ids", []) if str(value)
      ],
    )
    for item in raw_items
    if isinstance(item, dict)
  ]


def apply_board_overrides(
  catalog: list[CatalogItem],
  local_scripts: list[LocalScript],
  override_path: Path,
) -> int:
  if not override_path.exists():
    return 0
  overrides = json.loads(override_path.read_text(encoding="utf-8"))
  if not isinstance(overrides, dict):
    raise ValueError("帖子拆分表必须是 opus id 到剧本条目数组的对象")
  local_by_path = {script.path: script for script in local_scripts}
  result: list[CatalogItem] = []
  processed_ids: set[str] = set()
  changed = 0
  for item in catalog:
    raw_boards = overrides.get(item.opus_id)
    if raw_boards is None:
      result.append(item)
      continue
    if item.opus_id in processed_ids:
      continue
    processed_ids.add(item.opus_id)
    if not isinstance(raw_boards, list) or not raw_boards:
      raise ValueError(f"帖子拆分表条目必须是非空数组：{item.opus_id}")
    for raw_board in raw_boards:
      if not isinstance(raw_board, dict):
        raise ValueError(f"帖子拆分条目不是对象：{item.opus_id}")
      script_name = clean_space(raw_board.get("script_name"))
      local_path = clean_space(raw_board.get("local_json"))
      image_ids = [
        clean_space(value) for value in raw_board.get("source_image_ids", [])
        if clean_space(value)
      ]
      if not script_name or not image_ids:
        raise ValueError(f"帖子拆分条目缺少剧本名或原图：{item.opus_id}")
      local = local_by_path.get(local_path) if local_path else None
      if local_path and not local:
        raise ValueError(f"帖子拆分表中的 JSON 不存在或无法解析：{local_path}")
      result.append(CatalogItem(
        opus_id=item.opus_id,
        title=item.title,
        script_name=script_name,
        url=item.url,
        local_json=local.path if local else "",
        generated_image=local.generated_image if local else "",
        match_score=1.0 if local else 0.0,
        status="matched" if local else "unmatched",
        source_image_ids=image_ids,
      ))
    changed += 1
  catalog[:] = result
  return changed


def apply_match_overrides(
  catalog: list[CatalogItem],
  local_scripts: list[LocalScript],
  override_path: Path,
) -> int:
  if not override_path.exists():
    return 0
  overrides = json.loads(override_path.read_text(encoding="utf-8"))
  if not isinstance(overrides, dict):
    raise ValueError("人工匹配表必须是 opus id 到 JSON 路径的对象")
  local_by_path = {script.path: script for script in local_scripts}
  catalog_by_id = {item.opus_id: item for item in catalog}
  updated = 0
  for opus_id, local_path in overrides.items():
    item = catalog_by_id.get(str(opus_id))
    if not item:
      raise ValueError(f"人工匹配表中没有对应网页：{opus_id}")
    if local_path is None or not clean_space(local_path):
      if not item.local_json:
        continue
      item.local_json = ""
      item.generated_image = ""
      item.match_score = 0.0
      item.status = "unmatched"
      updated += 1
      continue
    local = local_by_path.get(clean_space(local_path))
    if not local:
      raise ValueError(f"人工匹配表中的 JSON 不存在或无法解析：{local_path}")
    if item.local_json == local.path:
      continue
    item.local_json = local.path
    item.generated_image = local.generated_image
    item.match_score = 1.0
    item.status = "matched"
    updated += 1
  return updated


def sync_catalog_local_artifacts(
  catalog: list[CatalogItem],
  local_scripts: list[LocalScript],
) -> int:
  local_by_path = {script.path: script for script in local_scripts}
  updated = 0
  for item in catalog:
    local = local_by_path.get(item.local_json)
    if not local or item.generated_image == local.generated_image:
      continue
    item.generated_image = local.generated_image
    updated += 1
  return updated


def prepare_and_review(
  item: CatalogItem,
  output_root: Path,
  refresh: bool,
  refresh_sources: bool,
  ocr_binary: Path | None,
  review_overrides: dict[str, Any],
) -> tuple[str, str]:
  try:
    folder = prepare_item(
      item,
      output_root,
      refresh=refresh,
      refresh_sources=refresh_sources,
    )
    if ocr_binary:
      review_item(folder, ocr_binary, review_overrides)
    return item.script_name, ""
  except Exception as error:
    return item.script_name, str(error)


def review_existing_folder(
  folder: Path,
  ocr_binary: Path,
  review_overrides: dict[str, Any],
) -> tuple[str, str]:
  try:
    metadata = json.loads((folder / "核对状态.json").read_text(encoding="utf-8"))
    sync_local_artifacts(folder, metadata)
    review_item(folder, ocr_binary, review_overrides)
    return folder.name, ""
  except Exception as error:
    return folder.name, str(error)


def existing_review_folders(output_root: Path, opus_ids: set[str]) -> list[Path]:
  folders = sorted(path.parent for path in (output_root / "剧本").glob("*/核对状态.json"))
  if not opus_ids:
    return folders
  return [
    folder for folder in folders
    if str(json.loads((folder / "核对状态.json").read_text(encoding="utf-8")).get("opus_id", ""))
    in opus_ids
  ]


def local_known_roster(path: str) -> set[str]:
  try:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return set()
  names: set[str] = set()
  known_names = known_character_names()
  for item in json_items(data):
    if clean_space(item.get("id")) == "_meta":
      continue
    team = clean_space(item.get("team")).lower()
    name = clean_space(item.get("name"))
    if not name or "jinx" in team or team in {"traveler", "travelers", "traveller", "traveller2"}:
      continue
    if name in known_names:
      names.add(name)
  return names


def roster_match_suggestions(
  catalog: list[CatalogItem],
  output_root: Path,
  local_scripts: list[LocalScript],
) -> list[dict[str, Any]]:
  local_rosters = [
    (script, local_known_roster(script.path)) for script in local_scripts
  ]
  suggestions: list[dict[str, Any]] = []
  for item in catalog:
    if item.local_json:
      continue
    folder = output_root / "剧本" / f"{safe_name(item.script_name)}-{item.opus_id}"
    metadata_path = folder / "核对状态.json"
    if not metadata_path.exists():
      continue
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_roster = set(metadata.get("ocr_heading_characters", []))
    if len(source_roster) < 8:
      continue
    scored: list[tuple[float, float, LocalScript, int, int]] = []
    for local, roster in local_rosters:
      if not roster:
        continue
      overlap = len(source_roster & roster)
      precision = overlap / len(source_roster)
      recall = overlap / len(roster)
      roster_score = min(precision, recall)
      if roster_score < 0.5:
        continue
      name_score = SequenceMatcher(
        None,
        normalize_script_name(item.script_name),
        local.normalized_name,
      ).ratio()
      scored.append((roster_score, name_score, local, overlap, len(roster)))
    scored.sort(key=lambda value: (value[0], value[1], value[2].path), reverse=True)
    if not scored:
      continue
    top_candidates = [
      {
        "local_json": candidate.path,
        "local_name": candidate.name,
        "roster_score": round(roster_score, 4),
        "name_score": round(name_score, 4),
        "overlap": overlap,
        "source_roster_count": len(source_roster),
        "local_roster_count": roster_count,
      }
      for roster_score, name_score, candidate, overlap, roster_count in scored[:3]
    ]
    best_score = scored[0][0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    suggestions.append({
      "script_name": item.script_name,
      "opus_id": item.opus_id,
      "source_roster": sorted(source_roster),
      "confident": best_score >= 0.85 and best_score - second_score >= 0.04,
      "candidates": top_candidates,
    })
  (output_root / "阵容匹配建议.json").write_text(
    json.dumps(suggestions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )
  return suggestions


def write_review_summary(output_root: Path) -> None:
  items: list[dict[str, Any]] = []
  for metadata_path in sorted((output_root / "剧本").glob("*/核对状态.json")):
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    items.append({
      "script_name": metadata.get("script_name", metadata_path.parent.name),
      "opus_id": metadata.get("opus_id", ""),
      "folder": str(metadata_path.parent),
      "status": metadata.get("review_status", "pending"),
      "missing_characters": metadata.get("ocr_missing_characters", []),
      "unexpected_characters": metadata.get("ocr_unexpected_characters", []),
      "ability_mismatches": metadata.get("ocr_ability_mismatches", []),
      "traveler_mismatches": metadata.get("ocr_traveler_mismatches", []),
      "jinx_mismatches": metadata.get("ocr_jinx_mismatches", []),
      "missing_jinx_rule_count": metadata.get("ocr_missing_jinx_rule_count", 0),
      "note_mismatches": metadata.get("ocr_note_mismatches", []),
      "unexplained_bottom_lines": metadata.get("ocr_unexplained_bottom_lines", []),
      "source_board_group_count": len(metadata.get("ocr_source_board_groups", [])),
    })
  status_counts: dict[str, int] = {}
  for item in items:
    status = str(item["status"])
    status_counts[status] = status_counts.get(status, 0) + 1
  payload = {
    "total": len(items),
    "status_counts": status_counts,
    "items": items,
  }
  (output_root / "核对汇总.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--json-root", type=Path, default=Path("all_jsons"))
  parser.add_argument("--output", type=Path, default=Path("bilibili_script_audit"))
  parser.add_argument("--catalog-only", action="store_true")
  parser.add_argument("--reuse-catalog", action="store_true")
  parser.add_argument("--matched-only", action="store_true")
  parser.add_argument("--opus-id", action="append", default=[])
  parser.add_argument("--start", type=int, default=0)
  parser.add_argument("--limit", type=int, default=0)
  parser.add_argument("--workers", type=int, default=4)
  parser.add_argument("--refresh", action="store_true")
  parser.add_argument("--refresh-sources", action="store_true")
  parser.add_argument("--review", action="store_true")
  parser.add_argument("--review-existing", action="store_true")
  parser.add_argument("--suggest-roster-matches", action="store_true")
  parser.add_argument(
    "--match-overrides",
    type=Path,
    default=Path("bilibili_match_overrides.json"),
  )
  parser.add_argument(
    "--board-overrides",
    type=Path,
    default=Path("bilibili_board_overrides.json"),
  )
  parser.add_argument(
    "--review-overrides",
    type=Path,
    default=Path("bilibili_review_overrides.json"),
  )
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  review_overrides = (
    json.loads(args.review_overrides.read_text(encoding="utf-8"))
    if args.review_overrides.exists() else {}
  )
  if not isinstance(review_overrides, dict):
    raise ValueError("人工核对表必须是 opus id 到核对记录的对象")
  catalog_path = args.output / "剧本清单.json"
  local_scripts = load_local_scripts(args.json_root)
  if args.reuse_catalog and catalog_path.exists():
    catalog = read_catalog(catalog_path)
  else:
    catalog = collect_catalog(ROOT_URL, local_scripts)
  board_override_count = apply_board_overrides(catalog, local_scripts, args.board_overrides)
  override_count = apply_match_overrides(catalog, local_scripts, args.match_overrides)
  artifact_count = sync_catalog_local_artifacts(catalog, local_scripts)
  if board_override_count or override_count or artifact_count or not catalog_path.exists() or not args.reuse_catalog:
    write_catalog(catalog, args.output)
  print(
    f"剧本条目 {len(catalog)}，匹配 JSON {sum(item.status == 'matched' for item in catalog)}，"
    f"未匹配 {sum(item.status != 'matched' for item in catalog)}。"
  )
  if args.review_existing:
    ocr_binary = build_ocr_tool(args.output)
    folders = existing_review_folders(args.output, set(args.opus_id))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
      futures = [
        executor.submit(review_existing_folder, folder, ocr_binary, review_overrides)
        for folder in folders
      ]
      for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
        name, error = future.result()
        if error:
          print(f"[{index}/{len(folders)}] 核对失败：{name}：{error}", file=sys.stderr)
        else:
          print(f"[{index}/{len(folders)}] 核对完成：{name}")
    write_review_summary(args.output)
    return
  if args.suggest_roster_matches:
    suggestions = roster_match_suggestions(catalog, args.output, local_scripts)
    print(
      f"阵容匹配建议 {len(suggestions)} 条，"
      f"高置信度 {sum(bool(item['confident']) for item in suggestions)} 条。"
    )
    return
  if args.catalog_only:
    return

  selected_ids = set(args.opus_id)
  selected = [
    item for item in catalog
    if (not args.matched_only or item.status == "matched")
    and (not selected_ids or item.opus_id in selected_ids)
  ]
  selected = selected[max(0, args.start):]
  selected = selected[:args.limit] if args.limit > 0 else selected
  ocr_binary = build_ocr_tool(args.output) if args.review else None
  workers = max(1, args.workers)
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
    futures = [
      executor.submit(
        prepare_and_review,
        item,
        args.output,
        args.refresh,
        args.refresh_sources,
        ocr_binary,
        review_overrides,
      )
      for item in selected
    ]
    for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
      name, error = future.result()
      if error:
        print(f"[{index}/{len(selected)}] 失败：{name}：{error}", file=sys.stderr)
      else:
        print(f"[{index}/{len(selected)}] 完成：{name}")


if __name__ == "__main__":
  main()
