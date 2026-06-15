#!/usr/bin/env python3
"""Apply targeted character fixes to the BOTC JSON collection."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = "all_jsons"
TEAM_ALIASES = {
  "demon": "demon",
  "demons": "demon",
  "minion": "minion",
  "minions": "minion",
  "恶魔": "demon",
  "爪牙": "minion",
}
NIGHT_ORDER_KEYS = ("firstNight", "otherNight")


def clean_text(value: Any) -> str:
  if value is None:
    return ""
  if isinstance(value, str):
    return re.sub(r"\s+", " ", value).strip()
  return str(value).strip()


def normalized_team(value: Any) -> str:
  return TEAM_ALIASES.get(clean_text(value).lower(), clean_text(value))


def json_paths(input_dir: Path) -> list[Path]:
  return sorted(
    path
    for path in input_dir.rglob("*")
    if path.is_file() and path.suffix.lower() == ".json"
  )


class CharacterFix:
  def __init__(self, name: str, teams: set[str], updates: dict[str, Any]) -> None:
    self.name = name
    self.teams = teams
    self.updates = updates

  def matches(self, item: dict[str, Any]) -> bool:
    return clean_text(item.get("name")) == self.name and normalized_team(item.get("team")) in self.teams

  def apply(self, item: dict[str, Any]) -> bool:
    if not self.matches(item):
      return False

    original_night_orders = {
      key: item[key]
      for key in NIGHT_ORDER_KEYS
      if key in item
    }
    changed = False
    for key, value in self.updates.items():
      if key in NIGHT_ORDER_KEYS:
        continue
      if item.get(key) != value:
        item[key] = value
        changed = True

    for key, value in original_night_orders.items():
      item[key] = value

    return changed


class CharacterFixRunner:
  def __init__(self, fixes: list[CharacterFix]) -> None:
    self.fixes = fixes

  def apply_to_data(self, data: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in self.iter_character_items(data):
      for fix in self.fixes:
        if fix.apply(item):
          counts[fix.name] += 1
    return counts

  def iter_character_items(self, data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
      return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
      items: list[dict[str, Any]] = []
      for key in ("characters", "roles", "script", "items", "data"):
        value = data.get(key)
        if isinstance(value, list):
          items.extend(item for item in value if isinstance(item, dict))
      if not items:
        items.append(data)
      return items
    return []

  def apply_to_file(self, path: Path, dry_run: bool) -> Counter[str]:
    original = path.read_text(encoding="utf-8-sig")
    data = json.loads(original)
    counts = self.apply_to_data(data)
    if counts and not dry_run:
      path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts


def demon_fix(name: str, updates: dict[str, Any]) -> CharacterFix:
  return CharacterFix(name=name, teams={"demon"}, updates=updates)


def minion_fix(name: str, updates: dict[str, Any]) -> CharacterFix:
  return CharacterFix(name=name, teams={"minion"}, updates=updates)


CHARACTER_FIXES = [
  CharacterFix(
    name="教父",
    teams={"minion"},
    updates={
      "ability": "在你的首个夜晚，你会得知有哪些外来者角色在场。如果有外来者在白天死亡，你会在当晚被唤醒并且你要选择一名玩家：他死亡。[-1或+1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/godfather.png",
      "firstNightReminder": "唤醒教父，对他展示外来者角色标记，告诉他有哪些外来者在场。",
      "otherNightReminder": "如果今天白天有外来者死亡，唤醒教父，让他攻击一名玩家。",
      "reminders": [
        "死于今日",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "通常来说，这只是件小事。但在你侮辱我女儿时，你就侮辱了我。你侮辱我，就侮辱了我的家族。你真的应该更小心些——要是你不幸发生意外事故，那就太遗憾了。",
    },
  ),
  demon_fix(
    name="小恶魔",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。如果你以这种方式自杀，一名爪牙会变成小恶魔。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/imp.png",
      "firstNightReminder": "",
      "otherNightReminder": "让小恶魔选择一名玩家。标记那名玩家死亡。如果小恶魔选择了自己：用一个备用的小恶魔标记替换一个存活的爪牙角色标记。让原来的小恶魔重新入睡。唤醒新的小恶魔。对他展示“你是”信息标记，和小恶魔角色标记。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我们必须让自己的头脑保持敏锐，刀刃保持锋利。邪恶在我们之中穿行，想要不择手段地摧毁我们的善良。那些愚蠢之辈，把我们美丽的小镇给毁了。不要相信任何人。但如果你一定要相信某人，请相信我。",
    },
  ),
  demon_fix(
    name="诺-达鲺",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。与你邻近的两名镇民中毒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/no_dashii.png",
      "firstNightReminder": "",
      "otherNightReminder": "让诺-达鲺选择一名玩家。标记那名玩家死亡。",
      "reminders": [
        "中毒",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "彼因汝之罪孽，吾已嗅汝之恶臭满溢全身。时日曷丧？予及汝皆亡。竖子命如草芥，以吾之力，使汝终末于深海，终于此良夜。",
    },
  ),
  demon_fix(
    name="亡骨魔",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。被你杀死的爪牙保留他的能力，且与他邻近的两名镇民之一中毒。[-1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/vigormortis.png",
      "firstNightReminder": "",
      "otherNightReminder": "让亡骨魔选择一名玩家。标记那名玩家死亡。如果该玩家是爪牙，标记该玩家保留能力，并标记与该玩家邻近的镇民玩家之一中毒。",
      "reminders": [
        "中毒",
        "保留能力",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "世间万扉集为一体，世间万匙铸为一身。世间万盅将与我共饮，但凡饮下我所赐圣水者，必将永不干渴，化作万孔泉眼涌作永生。",
    },
  ),
  demon_fix(
    name="方古",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。被该能力杀死的外来者改为变成邪恶的方古且你代替他死亡，但每局游戏仅能成功转化一次。[+1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fang_gu.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒方古，让他攻击一名玩家。如果该玩家是外来者并成功转化，则方古死亡，在他入睡后通知那名外来者角色变化。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [
        "限一次",
      ],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="普卡",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：他中毒。上个因你的能力中毒的玩家会死亡并恢复健康。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/pukka.png",
      "firstNightReminder": "让普卡选择一名玩家。标记那名玩家中毒。",
      "otherNightReminder": "唤醒普卡，让他选择一名玩家，该玩家中毒。上一个被普卡中毒的玩家死亡并恢复健康。",
      "reminders": [
        "中毒",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "您人真好，发生了这样的事情，您还愿意让我来您金碧辉煌的家里做客。我很抱歉，刚才不小心划伤了您。这是一点点赔礼，没事的，请收下吧，把这根金牙签当做我那卑微的歉意吧。",
    },
  ),
  demon_fix(
    name="涡流",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。镇民玩家的能力都会产生错误信息。如果白天没人被处决，邪恶阵营获胜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/vortox.png",
      "firstNightReminder": "",
      "otherNightReminder": "让涡流选择一名玩家。标记那名玩家死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "黑白颠倒，对错不再，左右变换，长短无猜。万物紊乱无可寻，短视死亡把命栽，何处寻答？随我来。",
    },
  ),
  demon_fix(
    name="珀",
    updates={
      "ability": "每个夜晚*，你可以选择一名玩家：他死亡。如果你上次选择时没有选择任何玩家，当晚你要选择三名玩家：他们死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/po.png",
      "firstNightReminder": "",
      "otherNightReminder": "珀可以选择一名玩家；或如果上一次他被唤醒时未做选择，让他选择三名玩家。标记这些玩家死亡。",
      "reminders": [
        "攻击三次",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="小怪宝",
    updates={
      "ability": "每个夜晚，所有爪牙要秘密决定由哪名玩家来照看小怪宝并且“是恶魔”。每个夜晚*，可能会有一名玩家死亡。[+1爪牙]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/lil_monsta.png",
      "firstNightReminder": "唤醒所有爪牙，允许他们以指向的方式决定谁照看小怪宝，但不能产生其他交流，否则会有非常糟糕的事情发生。",
      "otherNightReminder": "唤醒所有爪牙，允许他们以指向的方式决定谁照看小怪宝，但不能产生其他交流，否则会有非常糟糕的事情发生。说书人选择一名玩家，那名玩家死亡。",
      "reminders": [],
      "remindersGlobal": [
        "是恶魔",
        "死亡",
      ],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="痢蛭",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。在你的首个夜晚，你要选择一名存活的玩家：他中毒，只有当他处于死亡状态时你才会立即死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/lleech.png",
      "firstNightReminder": "唤醒痢蛭，让他选择一名玩家以寄生。",
      "otherNightReminder": "寄生蛭指向一名玩家。那名玩家死亡。",
      "reminders": [
        "中毒",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "美味，美味，美味，美味，美味，美味，美味，美味的脑——馅儿饼！是的。美味的老馅儿饼。我想说的就是这个。",
    },
  ),
  demon_fix(
    name="奥赫",
    updates={
      "ability": "每个夜晚*，你要选择一个角色：他死亡。如果该角色不在场，则由说书人来决定谁会被你杀死。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/ojo.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒奥赫，让他选择角色列表上的一个角色。该角色对应的玩家死亡，如果该角色不在场，替奥赫决定今晚谁会因为奥赫能力死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="卡扎力",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。[由你决定谁是什么爪牙，-或+任意数量外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/kazali.png",
      "firstNightReminder": "唤醒卡扎力，让他选择玩家变成邪恶爪牙。",
      "otherNightReminder": "唤醒卡扎力，让他攻击一名玩家。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="军团",
    updates={
      "ability": "每个夜晚*，可能有一名玩家死亡。如果一项提名只有邪恶玩家投票，投票无效。你也会被当作是爪牙。[半数以上玩家为军团]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/legion.png",
      "firstNightReminder": "",
      "otherNightReminder": "由说书人决定，让哪一名玩家死亡。",
      "reminders": [
        "即将被处决",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="牙噶巴卜",
    updates={
      "ability": "在你的首个夜晚，你会得知一段秘密短语。每次你在白天公开说出这段短语，当天便可能会有一名玩家在这之后死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/yaggababble.png",
      "firstNightReminder": "唤醒牙噶巴卜，对他展示他的秘密短语。",
      "otherNightReminder": "根据已放置的提示标记数量，选择最多等同于该数量的玩家死亡。该夜晚行动只是一个提示，死亡的造成时机可以是白天，也可以是夜晚的任何时候。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="饕餮",
    updates={
      "ability": "每个夜晚*，你要选择任意数量的非旅行者玩家或一名旅行者玩家：如果他们的角色类型均不相同，他们死亡。[+1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_5897997694761_fbe1f00c.jpg",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒饕餮，让其选择任意数量的玩家。如果这些玩家的角色类型均不相同，标记这些玩家死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="沙巴洛斯",
    updates={
      "ability": "每个夜晚*，你要选择两名玩家：他们死亡。你上个夜晚选择过且当前死亡的玩家之一可能会被你反刍。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/shabaloth.png",
      "firstNightReminder": "",
      "otherNightReminder": "上一夜被沙巴洛斯选择且当前已死亡的玩家之一可能被反刍，如果被反刍，标记那名玩家被复活。让沙巴洛斯选择两名玩家。标记这两名玩家死亡。",
      "reminders": [
        "复活",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="哈迪寂亚",
    updates={
      "ability": "每个夜晚*，你可以选择三名玩家（所有玩家会得知你选了谁）：他们分别秘密决定自己的生死，然后如果他们都存活则都死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/al-hadikhia.png",
      "firstNightReminder": "",
      "otherNightReminder": "哈迪寂亚选择三名玩家。对所有人宣告第一位玩家，然后唤醒他并让他秘密选择活着还是死去。依次对第二第三位玩家如此做。如果三名玩家都选择活着，他们都死去。",
      "reminders": [
        "1",
        "2",
        "3",
        "选择死",
        "选择生",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="堤丰之首",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。[邪恶玩家全部邻座，你位于正中，+1爪牙，-或+任意数量外来者]",
      "image": "https://clocktower-wiki.gstonegames.com/images/1/18/Lordoftyphon.png",
      "firstNightReminder": "将位于堤丰之首两侧的对应数量的玩家变成邪恶的爪牙，并分别唤醒他们通知他们的角色和阵营变化。",
      "otherNightReminder": "唤醒堤丰之首，让他攻击一名玩家。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  demon_fix(
    name="姑获鸟",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：他死亡。你可能会拥有上一个死于处决的爪牙的能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/guhuoniao.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒姑获鸟，让他攻击一名玩家。",
      "reminders": [
        "死亡",
        "获得能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="僵怖",
    updates={
      "ability": "每个夜晚*，如果今天白天没有人死亡，你会被唤醒并要选择一名玩家：他死亡。当你首次死亡后，你仍存活，但会被当作死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/zombuul.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果白天无人死亡，唤醒僵怖，让他攻击一名玩家。",
      "reminders": [
        "死于今日",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我不。明白。你的。方式。人类。同类。向我。指引。泥土。那是。圣地。静卧。安睡。我也。必须。长眠。立刻。",
    },
  ),
  demon_fix(
    name="典狱长",
    updates={
      "ability": "每个夜晚，你要选择至多三名玩家：如果明天白天他们之一死于处决，上次被你选择的其他玩家会在当晚死亡。否则，当晚他们之中会有一名玩家死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/dianyuzhang.png",
      "firstNightReminder": "唤醒典狱长，让其选择至多三名玩家。在这些玩家角色标记旁放置“囚禁”提示标记。",
      "otherNightReminder": "如果今天白天被处决的玩家标记有“囚禁”，则其他标记有囚禁的玩家死亡。否则，将其中一人标记为死亡。移除所有“囚禁”提示标记。唤醒典狱长，让其选择至多三名玩家。在这些玩家角色标记旁放置“囚禁”提示标记。",
      "reminders": [
        "囚禁",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="暴君",
    updates={
      "ability": "每个夜晚*，你可以选择至多两名玩家：他们死亡。你选择的玩家数量不能与上个夜晚死亡的玩家数量相同（超过二人时算作二人）。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/baojun.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒暴君，让他攻击至多两名玩家。但是暴君选择的玩家数量不能与上个夜晚死亡的玩家数量相同。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="利维坦",
    updates={
      "ability": "如果多于一名善良玩家被处决，邪恶阵营获胜。所有玩家都知道利维坦在场。在第五个白天结束时，邪恶阵营获胜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/role_icon/leviathan.png",
      "firstNightReminder": "放置利维坦的第一天标记，宣告利维坦在场，现在是第一天。",
      "otherNightReminder": "将利维坦的标记转换到下一天。",
      "reminders": [
        "善良被处决",
        "第一天",
        "第三天",
        "第二天",
        "第五天",
        "第四天",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  demon_fix(
    name="阎罗",
    updates={
      "ability": "在你的首个夜晚，你能查看魔典并选择一名玩家：他在第三个夜晚死亡，即使因为任何原因让他不会死亡。每个夜晚，你要选择一名玩家：上个夜晚被你选择的玩家死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202403/c_2190498760171_1c483826.jpg",
      "firstNightReminder": "唤醒阎罗，让他查看魔典。让阎罗选择一名玩家，将“三更将死”标记放置该玩家角色标记旁。之后再让阎罗选择一名玩家，将“即将死亡”标记放置该玩家角色标记旁。",
      "otherNightReminder": "让阎罗选择一名玩家，放置“即将死亡”标记在其角色图标旁。",
      "reminders": [
        "三更将死",
        "即将死亡",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
]


# Pending minion fixes from 投毒者 through 维齐尔. These are not applied until this script is run again.
# Skipped for now due material ability splits: 炸弹人, 街头风琴手, 酿酒师.
CHARACTER_FIXES.extend([
  minion_fix(
    name="投毒者",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：他在当晚和明天白天中毒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/poisoner.png",
      "firstNightReminder": "让投毒者选择一名玩家。标记那名玩家中毒。",
      "otherNightReminder": "让投毒者选择一名玩家。标记那名玩家中毒。",
      "reminders": [
        "中毒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="红唇女郎",
    updates={
      "ability": "如果大于等于五名玩家存活时（旅行者不计算在内）恶魔死亡，你变成那个恶魔。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/scarlet_woman.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果红唇女郎的能力曾被触发，唤醒她并告知她变成了哪个恶魔角色。",
      "reminders": [
        "是恶魔",
      ],
      "remindersGlobal": [
      ],
      "setup": 0,
      "flavor": "你曾向我展示了紫焰议会的秘密。我们也曾一起在烈火里拥抱，在欲望中交欢，在兽性的驱使下耳鬓厮磨，我将永生永世侍奉于你。但今晚，我亲爱的，我是你的主人。",
    },
  ),
  minion_fix(
    name="提线木偶",
    updates={
      "ability": "你以为你是一个善良角色，但其实你不是。恶魔会知道你是提线木偶。[提线木偶会与恶魔邻座]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/marionette.png",
      "firstNightReminder": "如果提线木偶在场，对恶魔展示提线木偶角色标记并指向提线木偶玩家。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [
        "是提线木偶",
      ],
      "setup": 1,
      "flavor": "",
    },
  ),
  minion_fix(
    name="刺客",
    updates={
      "ability": "每局游戏限一次，在夜晚时*，你可以选择一名玩家：他死亡，即使因为任何原因让他不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/assassin.png",
      "firstNightReminder": "",
      "otherNightReminder": "刺客可以选择一名玩家。如果他这么做了，标记那名玩家死亡，且刺客失去能力，之后的夜晚无需再唤醒刺客。",
      "reminders": [
        "失去能力",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="洗脑师",
    updates={
      "ability": "每个夜晚，你要选择一名玩家和一个善良角色。他明天白天和夜晚需要“疯狂”地证明自己是这个角色，不然他可能被处决。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/cerenovus.png",
      "firstNightReminder": "让洗脑师选择一名玩家和一个善良角色。标记那名玩家疯狂。让洗脑师重新入睡。唤醒洗脑师的目标。对这名玩家展示“该角色的能力对你生效”信息标记，洗脑师角色标记，该玩家需要疯狂证明的角色标记。",
      "otherNightReminder": "让洗脑师选择一名玩家和一个善良角色。标记那名玩家疯狂。让洗脑师重新入睡。唤醒洗脑师的目标。对这名玩家展示“该角色的能力对你生效”信息标记，洗脑师角色标记，该玩家需要疯狂证明的角色标记。",
      "reminders": [
        "疯狂",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "所谓的现实，其实，只是一种想法罢了。具体点来说，是我的想法。",
    },
  ),
  minion_fix(
    name="麻脸巫婆",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家和一个角色，如果该角色不在场，他变成该角色。如果因此创造了一个恶魔，当晚的死亡由说书人决定。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/pit-hag.png",
      "firstNightReminder": "",
      "otherNightReminder": "让麻脸巫婆选择一名玩家和一个角色。如果她选择的角色不在场：让麻脸巫婆重新入睡。唤醒她的目标玩家。对该玩家展示“你是”信息标记和他的新角色标记。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="魔鬼代言人",
    updates={
      "ability": "每个夜晚，你要选择一名存活的玩家（与上个夜晚不同）：如果明天白天他被处决，他不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/devils_advocate.png",
      "firstNightReminder": "让魔鬼代言人选择一名存活玩家。标记那名玩家处决不死。",
      "otherNightReminder": "让魔鬼代言人选择一名存活玩家，不能是上一夜他选择过的玩家。标记那名玩家处决不死。",
      "reminders": [
        "处决不死",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "如果异议被驳回，我的委托人将进行无罪申辩，理由是控方不遵守法规第27章B条——针对动词进行非正确或误导性的词形变化。昨晚有九名陪审团成员死亡，这个事实只不过是表面证据，正如威尔斯诉图勒案所开创的先例，这是无罪释放的进一步理由。",
    },
  ),
  minion_fix(
    name="鹰身女妖",
    updates={
      "ability": "每个夜晚，你要选择两名玩家：明天第一名玩家需要“疯狂”地证明第二名玩家是邪恶的，否则他们之中可能会有人死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/harpy.png",
      "firstNightReminder": "唤醒鹰身女妖并让他依次指向两名玩家。标记第一名玩家“疯狂”，标记第二名玩家“第二名”。",
      "otherNightReminder": "唤醒鹰身女妖并让他依次指向两名玩家。标记第一名玩家“疯狂”，标记第二名玩家“第二名”。",
      "reminders": [
        "疯狂",
        "第二名",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我从未见过如此光明的一日，阴森利爪不再笼罩着我。",
    },
  ),
  minion_fix(
    name="寡妇",
    updates={
      "ability": "在你的首个夜晚，你能查看魔典并选择一名玩家：他中毒。随后，始终会有一名善良玩家知道寡妇在场。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/widow.png",
      "firstNightReminder": "给寡妇展示魔典，她想看多久就看多久。等她看完后，让她指向一个玩家。那个玩家中毒。唤醒一名善良玩家，告诉他场上有寡妇。",
      "otherNightReminder": "",
      "reminders": [
        "中毒",
      ],
      "remindersGlobal": [
        "被知晓",
      ],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="女巫",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：如果他明天白天发起提名，他死亡。如果只有三名存活的玩家，你失去此能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/witch.png",
      "firstNightReminder": "让女巫选择一名玩家。标记那名玩家被诅咒。",
      "otherNightReminder": "让女巫选择一名玩家。标记那名玩家被诅咒。",
      "reminders": [
        "被诅咒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="精神病患者",
    updates={
      "ability": "每个白天，在提名开始前，你可以公开选择一名玩家：他死亡。如果你被处决，提名你的玩家需要和你猜拳，只有你输了你才会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/psychopath.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="间谍",
    updates={
      "ability": "每个夜晚，你能查看魔典。你可能会被当作善良阵营、镇民角色或外来者角色，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/spy.png",
      "firstNightReminder": "将魔典展示给间谍，他想看多久就看多久。",
      "otherNightReminder": "将魔典展示给间谍，他想看多久就看多久。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="哥布林",
    updates={
      "ability": "如果你在被提名后公开声明自己是哥布林且在那个白天被处决，你的阵营获胜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/goblin.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "已宣称",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "你不会想要侮辱哥布林的。你真的，真的不会。让我们换个话题……我能再吃一块蛋糕吗？",
    },
  ),
  minion_fix(
    name="男爵",
    updates={
      "ability": "会有额外的外来者在场。[+2 外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/baron.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "这个小镇没救了，不是么？廉价的外来劳动力……这就是问题所在。要我说，我会把他们全部调配到矿井里。不过是稍有些困难的工作，这不会伤害到任何人，要是有人提出反对意见就赏他一记耳光。这就是所谓的底线，不是么？",
    },
  ),
  minion_fix(
    name="科学怪人",
    updates={
      "ability": "恶魔拥有一个不在场的善良角色的能力，即使他醉酒或中毒。你和他都知道他获得了什么能力。",
      "image": "https://clocktower-wiki.gstonegames.com/images/f/f1/Boffin.png",
      "firstNightReminder": "（分别或同时）唤醒科学怪人和恶魔，通知他们恶魔因为科学怪人而获得的善良角色的能力。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "恒星的氢能，取之不尽，静待采掘；碳、氧、氖，尽数裂解。分子引发混沌，熵增由此产生，宇宙现象更替，原子紊乱重塑，物质聚合坍缩。所有的一切，都集中在这一个小小的锥形瓶中。",
    },
  ),
  minion_fix(
    name="限",
    updates={
      "ability": "在等同于初始外来者数量的夜晚，所有镇民玩家中毒直到下个黄昏。[外来者数量任意]",
      "image": "https://clocktower-wiki.gstonegames.com/images/b/b9/Xaan.png",
      "firstNightReminder": "如果夜晚天数等于初始外来者数量，所有镇民玩家中毒到下个黄昏。",
      "otherNightReminder": "如果夜晚天数等于初始外来者数量，所有镇民玩家中毒到下个黄昏。",
      "reminders": [
        "大限将至",
        "第一晚",
        "第三晚",
        "第二晚",
        "第四晚",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "他们接连倒下。一个，又一个。两个，三个，五个。",
    },
  ),
  minion_fix(
    name="召唤师",
    updates={
      "ability": "在首个夜晚，你会得知三个伪装。在第三个夜晚，你要选择一名玩家：他变成由你选择的邪恶恶魔。[无恶魔在场]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/summoner.png",
      "firstNightReminder": "唤醒召唤师，对他展示三个不在场的善良角色标记。",
      "otherNightReminder": "如果这是游戏中的第三个夜晚，唤醒召唤师，让他选择一名玩家和一个恶魔角色，那名玩家变成由他选择的邪恶恶魔。",
      "reminders": [
        "第一晚",
        "第三晚",
        "第二晚",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  minion_fix(
    name="灵言师",
    updates={
      "ability": "在你的首个夜晚，你会得知一个关键词。首个说出该关键词的善良玩家会在当晚转变为邪恶阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/mezepheles.png",
      "firstNightReminder": "唤醒灵言师，对他展示他的关键词。",
      "otherNightReminder": "唤醒第一个说出灵言师词语的玩家并告知他已经变成邪恶阵营。",
      "reminders": [
        "失去能力",
        "转为邪恶",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="蛊雕",
    updates={
      "ability": "每个夜晚，你要选择左或右：你得知该方向上的下一名存活善良玩家的角色，他中毒且其他善良玩家以为他是邪恶的蛊雕，直到下个黄昏。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_4078497694761_5c6ddcce.jpg",
      "firstNightReminder": "唤醒蛊雕，让其选择一个方向。将他的“中毒”标记移动至那个方向上的下一个存活玩家的角色标记旁。随后对他指向那名玩家，并展示“他是”提示标记和该玩家的角色标记。",
      "otherNightReminder": "唤醒蛊雕，让其选择一个方向。将他的“中毒”标记移动至那个方向上的下一个存活玩家的角色标记旁。随后对他指向那名玩家，并展示“他是”提示标记和该玩家的角色标记。",
      "reminders": [
        "中毒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "献上你能出的最高筹码，否则蛊毒入体，无力回天。",
    },
  ),
  minion_fix(
    name="主谋",
    updates={
      "ability": "如果恶魔因为死于处决而因此导致游戏结束时，再额外进行一个夜晚和一个白天。在那个白天如果有玩家被处决，他的阵营落败。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/mastermind.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": ["主谋日"],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "怪物的触手被钉在了教堂大门上。母亲和孩子们在街上跳舞。棒极了。一切都在按我的计划进行。",
    },
  ),
  minion_fix(
    name="镜像双子",
    updates={
      "ability": "你与一名对立阵营的玩家互相知道对方是什么角色。如果其中善良玩家被处决，邪恶阵营获胜。如果你们都存活，善良阵营无法获胜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/evil_twin.png",
      "firstNightReminder": "唤醒镜像双子和他的对立双子，让他们进行眼神接触。对镜像双子展示对立双子的角色标记，并对对立双子展示镜像双子的角色标记。",
      "otherNightReminder": "",
      "reminders": [
        "对立双子",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="狐媚娘",
    updates={
      "ability": "在你的首个夜晚，你要选择一名玩家：他会知道狐媚娘在场。如果你死于处决，当晚他转变为邪恶阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/humeiniang.png",
      "firstNightReminder": "唤醒狐媚娘，让她选择一名玩家。标记那名玩家“被魅惑”。随后唤醒那名玩家，对他展示“该角色的能力对你触发”和狐媚娘角色标记。",
      "otherNightReminder": "如果今日狐媚娘死于处决，且被魅惑的玩家为善良阵营，唤醒被魅惑的玩家，对他展示“你是”和朝下的大拇指。",
      "reminders": [
        "被魅惑",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="养蛊人",
    updates={
      "ability": "在你存活时提名你的玩家会在当晚死亡，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/yangguren.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果有玩家被放置了“提名”标记，标记该玩家死亡。",
      "reminders": [
        "提名",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "把毒蛇、蝎子、蜈蚣、蟾蜍、蜘蛛放在一起……多！来！点！",
    },
  ),
  minion_fix(
    name="赶尸人",
    updates={
      "ability": "与你邻近的两名镇民玩家会在其首次死亡时被当作仍然存活。[-1外来者]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_4215797694761_97f10b13.jpg",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "以为存活",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  minion_fix(
    name="巫师",
    updates={
      "ability": "每局游戏限一次，你可以向说书人许愿。如果愿望被实现，可能会伴随着代价和线索。",
      "image": "https://clocktower-wiki.gstonegames.com/images/archive/c/c7/20250103031516%21Wizard.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "代价",
        "兑现",
        "失去能力",
        "线索",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="画皮",
    updates={
      "ability": "在你的首个夜晚，你要选择一名存活玩家：他死亡但会被当作存活。当他下一次死亡时，他重生，随后你重获能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202403/c_8796728760171_7caa0950.jpg",
      "firstNightReminder": "唤醒画皮，让画皮选择一名存活玩家，那名存活玩家变成活尸。",
      "otherNightReminder": "如果首夜被画皮变成活尸的玩家死亡，他重生，然后画皮重获能力。唤醒画皮，让画皮选择一名存活玩家，那名存活玩家变成活尸。",
      "reminders": [
        "以为存活",
        "重获能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="恐惧之灵",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：如果你提名他且他被处决，他的阵营落败。当你首次选择或更换目标时，所有玩家都会得知你选择了新的玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fearmonger.png",
      "firstNightReminder": "恐惧之灵指向一名玩家，放置恐惧标记。宣布恐惧之灵选中或改变了目标。",
      "otherNightReminder": "恐惧之灵指向一名玩家。如果与之前选择的不同，则更换恐惧标记并宣布恐惧之灵选中或改变了目标。",
      "reminders": [
        "恐惧",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  minion_fix(
    name="维齐尔",
    updates={
      "ability": "所有玩家都知道你是维齐尔。你在白天时不会死亡。如果一次提名中有善良玩家投票，你可以让被提名者立即被处决。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/vizier.png",
      "firstNightReminder": "如果维齐尔在场，告知所有人谁是维齐尔。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
])


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Apply specific character fixes to BOTC JSON files.")
  parser.add_argument(
    "--input-dir",
    default=DEFAULT_INPUT_DIR,
    help=f"Directory containing JSON files. Default: {DEFAULT_INPUT_DIR}",
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Report fixes without writing files.",
  )
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  runner = CharacterFixRunner(CHARACTER_FIXES)
  input_dir = Path(args.input_dir)
  total_counts: Counter[str] = Counter()
  changed_files = 0
  failed_files: list[tuple[Path, str]] = []

  for path in json_paths(input_dir):
    try:
      counts = runner.apply_to_file(path, args.dry_run)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
      failed_files.append((path, str(exc)))
      continue
    if counts:
      changed_files += 1
      total_counts.update(counts)

  action = "Would update" if args.dry_run else "Updated"
  print(f"{action} {changed_files} files")
  for name, count in sorted(total_counts.items()):
    print(f"{name}: {count} character entries")
  if failed_files:
    print(f"Skipped {len(failed_files)} unreadable JSON files")
    for path, error in failed_files[:20]:
      print(f"- {path}: {error}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
