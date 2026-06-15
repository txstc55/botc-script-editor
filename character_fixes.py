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
  "outsider": "outsider",
  "outsiders": "outsider",
  "townfolk": "townsfolk",
  "townsfolk": "townsfolk",
  "townsfolks": "townsfolk",
  "恶魔": "demon",
  "外来者": "outsider",
  "外来角色": "outsider",
  "镇民": "townsfolk",
  "镇民角色": "townsfolk",
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


def outsider_fix(name: str, updates: dict[str, Any]) -> CharacterFix:
  return CharacterFix(name=name, teams={"outsider"}, updates=updates)


def townsfolk_fix(name: str, updates: dict[str, Any]) -> CharacterFix:
  return CharacterFix(name=name, teams={"townsfolk"}, updates=updates)


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


# Minion fixes from 投毒者 through 维齐尔.
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


# Outsider fixes from 酒鬼 through 使节.
# Skipped for now due material ability splits: 书生, 使节.
CHARACTER_FIXES.extend([
  outsider_fix(
    name="酒鬼",
    updates={
      "ability": "你不知道你是酒鬼。你以为你是一个镇民角色，但其实你不是。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/drunk.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [
        "是酒鬼",
      ],
      "setup": 1,
      "flavor": "我是个只在社交场合里~嗝儿~喝酒的人，亲爱的。 但无可否认，我是一个非常~嗝儿~擅长社交的人。",
    },
  ),
  outsider_fix(
    name="陌客",
    updates={
      "ability": "你可能会被当作邪恶阵营、爪牙角色或恶魔角色，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/recluse.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "侬康康窝咦锅惹，咋锅就怼窝恁锅粗暴。介样叭行。麻绳添酒嘿料，泥滴燕绳恨舔没，窝这哈圆酿泥料！侬晓得伐！窝叭象载康岛泥鸟，辣过饿魔阔能揍载窝家边乱晃。呔！窝揍斯弄个以斯！",
    },
  ),
  outsider_fix(
    name="畸形秀演员",
    updates={
      "ability": "如果你“疯狂”地证明自己是外来者，你可能被处决。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/mutant.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我不是怪物！我是人！求你了！",
    },
  ),
  outsider_fix(
    name="理发师",
    updates={
      "ability": "如果你死亡，在当晚恶魔可以选择两名玩家（不能选择其他恶魔）交换角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/barber.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果理发师今天死亡了，唤醒恶魔并展示“该角色的效果对你生效”信息标记和理发师角色标记。如果恶魔选择了两名玩家，将这两名玩家分别独自唤醒。对他们展示“你是”信息标记和他们的新角色标记。",
      "reminders": [
        "今晚理发",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "对了，你以前知不知道，理发师和手术医生其实是同一个职业？不知道？那现在你知道了。",
    },
  ),
  outsider_fix(
    name="疯子",
    updates={
      "ability": "你以为你是一个恶魔，但其实你不是。恶魔知道你是疯子以及你在每个夜晚选择了哪些玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/lunatic.png",
      "firstNightReminder": "如果有七名或更多玩家，唤醒疯子：展示“他们是你的爪牙”信息标记。指向任意对应数量的玩家。展示“这些角色不在场”信息标记。展示三个善良角色。让疯子重新入睡。唤醒恶魔。展示“你是”信息标记和恶魔角色标记。展示“这名玩家是”信息标记和疯子角色标记，然后指向疯子玩家。",
      "otherNightReminder": "做任何需要做的事情来模拟一位恶魔的行动。让疯子重新入睡。唤醒恶魔。对恶魔展示疯子角色标记，并指向疯子玩家，随后是疯子的攻击目标。",
      "reminders": [],
      "remindersGlobal": [
        "是疯子",
        "被选择",
      ],
      "setup": 0,
      "flavor": "吾即是暗夜……没错吧？",
    },
  ),
  outsider_fix(
    name="落难少女",
    updates={
      "ability": "所有爪牙都知道落难少女在场。每局游戏限一次，任意爪牙可以公开猜测你是落难少女，如果猜对，你的阵营落败。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/damsel.png",
      "firstNightReminder": "如果落难少女在场，对爪牙展示落难少女角色标记。",
      "otherNightReminder": "0",
      "reminders": [
        "已被猜测",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="月之子",
    updates={
      "ability": "当你得知你死亡时，你要公开选择一名存活的玩家。如果他是善良的，在当晚他会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/moonchild.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果月之子在白天触发了死亡能力并选择了一名善良玩家，该玩家死亡。标记那名玩家死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "天蝎座侧身遥望恋人，此刻即为抉择进行之时。以白银拂过我的掌心，你的宿命将在此地揭示。以钢铁穿过我的咽喉，群星在上你将追悔莫及。",
    },
  ),
  outsider_fix(
    name="呆瓜",
    updates={
      "ability": "当你得知你死亡时，你要公开选择一名存活的玩家：如果他是邪恶的，你的阵营落败。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/klutz.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="解谜大师",
    updates={
      "ability": "一名玩家醉酒，即使你已死亡。每局游戏限一次，你可以猜测谁是那个醉酒的玩家，如果猜对了，你会得知谁是恶魔，但如果猜错了，你会得知错误的“谁是恶魔”信息。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/puzzlemaster.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "已猜测",
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="魔像",
    updates={
      "ability": "每局游戏你只能发起提名一次。当你发起提名时，如果被你提名的玩家不是恶魔，他死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/golem.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "无法提名",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="心上人",
    updates={
      "ability": "当你死亡时，会有一名玩家开始醉酒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/sweetheart.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果心上人死亡，会有一名玩家立刻醉酒。如果你还没有让这件事情发生，那么现在为任意一位玩家放置醉酒标记。",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我永远也忘不掉她……永远……",
    },
  ),
  outsider_fix(
    name="修补匠",
    updates={
      "ability": "你随时可能死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/tinker.png",
      "firstNightReminder": "",
      "otherNightReminder": "修补匠可能会死亡。如果说书人选择让修补匠死亡，放置死亡标记。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="莽夫",
    updates={
      "ability": "每个夜晚，首个使用其自身能力选择了你的玩家会醉酒直到下个黄昏。你会转变为他的阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/goon.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "是的，老大。我跟那个家伙好好解释过了。他不愿意再听我解释一遍。不不，老大，我不需要医生——只是刀伤而已。明天早上就好了。",
    },
  ),
  outsider_fix(
    name="政客",
    updates={
      "ability": "如果你是对你的阵营落败负最大责任的人，你转变阵营并获胜，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/politician.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="瘟疫医生",
    updates={
      "ability": "当你死亡时，说书人会获得一个爪牙能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/plague_doctor.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果瘟疫医生死亡，说书人获得一项爪牙能力。",
      "reminders": [
        "说书人能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "辟免剧勒润动。输要时间康护。莫要，抹药。",
    },
  ),
  outsider_fix(
    name="帽匠",
    updates={
      "ability": "如果你死亡，当晚爪牙和恶魔玩家可以选择变成新的爪牙和恶魔角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/hatter.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果帽匠死于白天，（建议分别）唤醒恶魔和爪牙并让他们选择是否改变角色。如果帽匠死于夜晚，则在当前玩家行动结束后立即开始茶会。",
      "reminders": [
        "今晚茶会",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="圣徒",
    updates={
      "ability": "如果你死于处决，你的阵营落败。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/saint.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="逆臣",
    updates={
      "ability": "在你的首个夜晚，你要选择除你以外的一名玩家：如果他先死于处决，你转变为邪恶；如果你先死于处决，他转变为邪恶。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/nichen.png",
      "firstNightReminder": "唤醒逆臣，让其选择一名玩家。在该玩家的角色标记旁放置“不共戴天”提示标记。",
      "otherNightReminder": "如果逆臣或标记了“不共戴天”的玩家死于处决，唤醒两者之中的另一名玩家，告诉他变为邪恶阵营。",
      "reminders": [
        "不共戴天",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "尔遣使遗尔舅祖总兵书，朕已洞悉。将军之心，犹豫未决。朕恐将军失次机会，殊可惜耳。",
    },
  ),
  outsider_fix(
    name="告密者",
    updates={
      "ability": "爪牙会在其首个夜晚得知三个伪装。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/snitch.png",
      "firstNightReminder": "如果告密者在场，对爪牙展示三个不在场的善良角色标记。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="狂热者",
    updates={
      "ability": "如果有大于等于五名玩家存活，你必须在所有提名中投票。",
      "image": "https://clocktower-wiki.gstonegames.com/images/1/1a/Zealot.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="食人魔",
    updates={
      "ability": "在你的首个夜晚，你要选择除你以外的一名玩家：你转变为他的阵营，即使你已醉酒或中毒，但你不知道你转变后的阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/ogre.png",
      "firstNightReminder": "唤醒食人魔，让他选择一名玩家。如果他选择了邪恶玩家，将他的角色标记在魔典中倒置以表示他转变为邪恶阵营。",
      "otherNightReminder": "",
      "reminders": [
        "挚友",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "<咽口水><咧嘴笑><咽口水>",
    },
  ),
  outsider_fix(
    name="入殓师",
    updates={
      "ability": "如果你提名并处决了恶魔，你会变成邪恶的恶魔。当剩余存活玩家小于等于四人时（旅行者除外），你失去能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_5757097694761_2de60c7b.jpg",
      "firstNightReminder": "",
      "otherNightReminder": "如果白天入殓师提名了恶魔且恶魔被处决，唤醒他，并对他展示“你是”提示标记和恶魔角色标记。",
      "reminders": [
        "是恶魔",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="异端分子",
    updates={
      "ability": "对调胜负结果，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/heretic.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="杂技演员",
    updates={
      "ability": "每个夜晚*，如果与你邻近的存活善良玩家之一醉酒或中毒，你死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/acrobat.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果杂技演员左右两侧最近的存活善良玩家之一中毒或醉酒，杂技演员死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="煞星",
    updates={
      "ability": "如果你死亡，当晚与你邻近的存活玩家之一可能会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/shaxing.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果煞星死亡，决定是否让一名与他邻近的存活玩家死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="管家",
    updates={
      "ability": "每个夜晚，你要选择除你以外的一名玩家：明天白天，只有他投票时你才能投票。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/butler.png",
      "firstNightReminder": "让管家选择一名玩家。标记那名玩家为他的主人。",
      "otherNightReminder": "让管家选择一名玩家。标记那名玩家为他的主人。",
      "reminders": [
        "主人",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="酒保",
    updates={
      "ability": "与你邻近的善良玩家之一醉酒，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/jiubao.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  outsider_fix(
    name="隐士",
    updates={
      "ability": "你拥有所有外来者能力。[-0~1外来者]",
      "image": "https://clocktower-wiki.gstonegames.com/images/1/1e/Hermit.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [
        "是隐士",
      ],
      "setup": 1,
      "flavor": "于尘寰遗忘之境，有光静静亮着，不问归期。",
    },
  ),
  outsider_fix(
    name="书童",
    updates={
      "ability": "在你的首个夜晚，你要选择除你以外的一名玩家：除首个夜晚以外，当他被邪恶玩家的能力选择或影响时，你会在当晚死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202404/c_2027903943171_36d374a5.jpg",
      "firstNightReminder": "唤醒书童，让其选择一名玩家，在其选择的玩家标记旁放置“选择”。",
      "otherNightReminder": "如果标记有“选择”的玩家被邪恶玩家的能力选择或影响时，在书童旁放置“死亡”标记。",
      "reminders": [
        "死亡",
        "选择",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
])

# Townsfolk fixes from 博学者 through 戏子.
# Skipped for now due material ability splits: 气球驾驶员, 炼金术士, 阴阳师, 钦天监, 半兽人, 郎中, 提刑官, 鸩, 国王, 道士, 巡察, 知府, 打更人, 熊孩子, 狸猫, 俑匠, 戏子.
CHARACTER_FIXES.extend([
  townsfolk_fix(
    name="博学者",
    updates={
      "ability": "每个白天，你可以私下询问说书人以得知两条信息：一个是正确的，一个是错误的。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/savant.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "地上有七十二根火柴……今天的太阳落得更早，月亮还是按时升起……一块破布……庄园里的邪恶之物……三个又三个……我们相信的事物和他真正看到的不一样……绿光代表镁……残留物，但是图案不太对……地上有七十二根火柴……",
    },
  ),
  townsfolk_fix(
    name="占卜师",
    updates={
      "ability": "每个夜晚，你要选择两名玩家：你会得知他们之中是否有恶魔。会有一名善良玩家始终被你的能力当作恶魔。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fortune_teller.png",
      "firstNightReminder": "让占卜师选择两名玩家。如果其中有恶魔或“干扰项”，点头示意，否则摇头。",
      "otherNightReminder": "让占卜师选择两名玩家。如果其中有恶魔或“干扰项”，点头示意，否则摇头。",
      "reminders": [
        "干扰项",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我在你的灵魂中感受到了庞大的恶意！但……那可能只是你的香水味道。我对接骨木汁过敏。",
    },
  ),
  townsfolk_fix(
    name="食人族",
    updates={
      "ability": "你拥有上个死于处决的玩家的能力。如果该玩家属于邪恶阵营，你中毒直到下个善良玩家死于处决。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/cannibal.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "中毒",
        "饱餐",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我讨厌小丑的味道。吃起来会让我想笑。",
    },
  ),
  townsfolk_fix(
    name="女裁缝",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择除你以外的两名玩家：你会得知他们是否为同一阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/seamstress.png",
      "firstNightReminder": "女裁缝可以选择除自己以外的两名玩家。如果她这么做了，对她点头或摇头示意这两名玩家是否为同一阵营，随后标记女裁缝失去能力。之后的夜晚无需再唤醒女裁缝。",
      "otherNightReminder": "女裁缝可以选择除自己以外的两名玩家。如果她这么做了，对她点头或摇头示意这两名玩家是否为同一阵营，随后标记女裁缝失去能力。之后的夜晚无需再唤醒女裁缝。",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "你听到那个穿羊绒大衣的家伙对我们小贝尔说什么了吗？他说……‘好’？哎，行吧，和哈利还有那个杂耍艺人那一出相比，这算不了什么。说什么？我可不说，我又不是什么长舌妇。",
    },
  ),
  townsfolk_fix(
    name="共情者",
    updates={
      "ability": "每个夜晚，你会得知与你邻近的两名存活的玩家中邪恶玩家的数量。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/empath.png",
      "firstNightReminder": "给他展示数字手势来告诉他与他邻近的存活玩家有几人是邪恶的。",
      "otherNightReminder": "给他展示数字手势来告诉他与他邻近的存活玩家有几人是邪恶的。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我的皮肤有些刺痛。这有些不太对劲。我能感觉得到。",
    },
  ),
  townsfolk_fix(
    name="贵族",
    updates={
      "ability": "在你的首个夜晚，你会得知三名玩家：其中有且只有一名玩家是邪恶的。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/noble.png",
      "firstNightReminder": "以任意顺序指向三名玩家，其中一名邪恶。",
      "otherNightReminder": "",
      "reminders": [
        "被得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "讽刺的确是最不足挂齿的机智。尽管如此，先生，回应你的批评，就是一种机智。",
    },
  ),
  townsfolk_fix(
    name="赌徒",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家并猜测该玩家的角色：如果你猜错了，你会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/gambler.png",
      "firstNightReminder": "",
      "otherNightReminder": "让赌徒选择一名玩家和一个角色。如果赌徒猜错了，标记赌徒死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "正面，我赢。 反面，你输。",
    },
  ),
  townsfolk_fix(
    name="哲学家",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择一个善良角色：你获得该角色的能力。如果这个角色在场，他醉酒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/philosopher.png",
      "firstNightReminder": "哲学家可以选择一个角色。如果选择的角色不在场，将哲学家的角色标题替换成对应角色，并标记“是哲学家”，否则标记该角色对应的玩家醉酒。从现在开始，你需要以哲学家获得能力的那种角色的行动方式来唤醒哲学家。",
      "otherNightReminder": "哲学家可以选择一个角色。如果选择的角色不在场，将哲学家的角色标题替换成对应角色，并标记“是哲学家”，否则标记该角色对应的玩家醉酒。从现在开始，你需要以哲学家获得能力的那种角色的行动方式来唤醒哲学家。",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [
        "是哲学家",
      ],
      "setup": 0,
      "flavor": "如果你要说什么事情是最真实的？我想是啤酒。痛快喝吧，说不定我们明天就要死了。",
    },
  ),
  townsfolk_fix(
    name="造谣者",
    updates={
      "ability": "每个白天，你可以公开发表一个声明。如果该声明正确，在当晚会有一名玩家死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/gossip.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果白天的声明为真，会有一名玩家死亡，并由说书人来选择一名玩家，标记该玩家死亡。",
      "reminders": [
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉巴拉。巴拉。",
    },
  ),
  townsfolk_fix(
    name="侍女",
    updates={
      "ability": "每个夜晚，你要选择除你以外的两名存活的玩家：你会得知他们中有几人在当晚因其自身能力而被唤醒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/chambermaid.png",
      "firstNightReminder": "唤醒侍女，让她选择两名除自己以外的存活玩家。用手势比划数字来告知她这些玩家中因自己能力而唤醒的玩家数量。",
      "otherNightReminder": "唤醒侍女，让她选择两名除自己以外的存活玩家。用手势比划数字来告知她这些玩家中因自己能力而唤醒的玩家数量。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我没有看到任何不寻常的事，夫人。请原谅我，但要是我真的看到了什么，那一定不是屋子主人在大约十一点的时候溜进了教授的实验室还把那些花花绿绿的药剂混合在了一起，就如你所说的那样，女士。",
    },
  ),
  townsfolk_fix(
    name="城镇公告员",
    updates={
      "ability": "每个夜晚*，你会得知在今天白天时是否有爪牙发起过提名。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/town_crier.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒城镇公告员，以点头或摇头告知他今天白天是否有爪牙发起提名。",
      "reminders": [
        "爪牙已提名",
        "爪牙未提名",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="僧侣",
    updates={
      "ability": "每个夜晚*，你要选择除你以外的一名玩家：当晚恶魔的负面能力对他无效。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/monk.png",
      "firstNightReminder": "",
      "otherNightReminder": "让僧侣选择除自己外的一名玩家。标记那名玩家被保护。",
      "reminders": [
        "保护",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="神谕者",
    updates={
      "ability": "每个夜晚*，你会得知有多少名死亡的玩家是邪恶的。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/oracle.png",
      "firstNightReminder": "",
      "otherNightReminder": "给他展示数字手势来告诉他当前已死亡的玩家中有多少玩家是邪恶的。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "唯有受选者才能凝视面纱之外的光景。亡者躁动不安……他们的每一根僵硬的手指都指向了刺骨的北地。",
    },
  ),
  townsfolk_fix(
    name="小精灵",
    updates={
      "ability": "在你的首个夜晚，你会得知一个在场的镇民角色。如果你“疯狂”地证明你是该角色，当他死亡时你获得该角色的能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/pixie.png",
      "firstNightReminder": "对小精灵展示一个在场的镇民角色。",
      "otherNightReminder": "",
      "reminders": [
        "疯狂",
        "获得能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "绕着花园转圈圈，女孩跑得疯癫癫。男孩树上荡秋千，小精灵在谁心间？淑女微笑小镇边，贵族抡斧树长眠。容貌相似难分辨，谜底揭晓圣光现：小精灵呀是神仙。",
    },
  ),
  townsfolk_fix(
    name="筑梦师",
    updates={
      "ability": "每个夜晚，你要选择除你及旅行者以外的一名玩家：你会得知一个善良角色和一个邪恶角色，该玩家是其中一个角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/dreamer.png",
      "firstNightReminder": "让筑梦师指向一名玩家。对他展示善良和邪恶的角色标记各一个，其中一个是属于该玩家的角色。",
      "otherNightReminder": "让筑梦师指向一名玩家。对他展示善良和邪恶的角色标记各一个，其中一个是属于该玩家的角色。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我记得有钟表匠……天空是红色的，有不规则的三角形不断从天上坠落下来。有紫罗兰的气味……还有气泡咕嘟咕嘟的声音。一个眼睛发光、还有着乱糟糟的胡须的女人对着天空发出嘶嘶声。然后，我醒了……",
    },
  ),
  townsfolk_fix(
    name="渔夫",
    updates={
      "ability": "每局游戏限一次，在白天时，你可以让说书人给你一些能帮助你的阵营获胜的建议。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fisherman.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="舞蛇人",
    updates={
      "ability": "每个夜晚，你要选择一名存活的玩家：如果你选中了恶魔，你和他交换角色和阵营，然后他中毒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/snake_charmer.png",
      "firstNightReminder": "让舞蛇人选择一名玩家。如果舞蛇人选中了恶魔：展示“你是”信息标记和恶魔角色标记。用拇指向下代表他阵营变为邪恶。在魔典中交换舞蛇人和恶魔的角色标记。让原来的舞蛇人重新入睡。唤醒原来的恶魔。对老恶魔展示“你是”信息标记和舞蛇人角色标记，并用拇指向上代表他阵营变为善良。",
      "otherNightReminder": "让舞蛇人选择一名玩家。如果舞蛇人选中了恶魔：展示“你是”信息标记和恶魔角色标记。用拇指向下代表他阵营变为邪恶。在魔典中交换舞蛇人和恶魔的角色标记。让原来的舞蛇人重新入睡。唤醒原来的恶魔。对老恶魔展示“你是”信息标记和舞蛇人角色标记，并用拇指向上代表他阵营变为善良。",
      "reminders": [
        "中毒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "这位老爷……虽然我的烟斗是金色的，虽然我只要一首曲子就能驯服最狂野的灯神，但我只是一个卑贱的舞蛇人罢了，哎……听天由命吧。俗话说，人心不足蛇吞象。但不是我，这位老爷……真的不是我。",
    },
  ),
  townsfolk_fix(
    name="祖母",
    updates={
      "ability": "在你的首个夜晚，你会得知一名善良玩家和他的角色。如果恶魔杀死了他，你也会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/grandmother.png",
      "firstNightReminder": "指向她的孙子玩家，并展示该玩家的角色标记。",
      "otherNightReminder": "如果孙子被恶魔杀死，祖母也会一同死亡。标记祖母死亡。",
      "reminders": [
        "孙子",
        "死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="厨师",
    updates={
      "ability": "在你的首个夜晚，你会得知场上邻座的邪恶玩家有多少对。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/chef.png",
      "firstNightReminder": "给他展示数字手势来告诉他场上邻座邪恶玩家有多少对。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "今晚的预约有些古怪。我从未见过梅威瑟太太此前跟那个哈德逊巷的流氓有过交情。 然而今晚，他们订了一张双人桌。真奇怪。",
    },
  ),
  townsfolk_fix(
    name="守鸦人",
    updates={
      "ability": "如果你在夜晚死亡，你会被唤醒，然后你要选择一名玩家：你会得知他的角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/ravenkeeper.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果守鸦人今晚死亡，唤醒他并让他选择一名玩家。对他展示那名玩家的角色标记。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我的鸟儿们会替我复仇的！飞吧！飞吧，我尽职的小可爱！去到庄园和溪边！去到小巷和集会所里！快飞吧！",
    },
  ),
  townsfolk_fix(
    name="旅店老板",
    updates={
      "ability": "每个夜晚*，你要选择两名玩家：他们当晚不会死亡，但其中一人会醉酒到下个黄昏。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/innkeeper.png",
      "firstNightReminder": "",
      "otherNightReminder": "让旅店老板选择两名玩家。标记这两名玩家不会死亡，并标记其中一人醉酒。",
      "reminders": [
        "不会死亡",
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="艺术家",
    updates={
      "ability": "每局游戏限一次，在白天时，你可以私下询问说书人一个是非问题，你会得知该问题的答案。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/artist.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "天啊！多么美妙的作品！我的作品……用你们的话怎么说来着……对，璀璨夺目！栩栩如生！没错！",
    },
  ),
  townsfolk_fix(
    name="图书管理员",
    updates={
      "ability": "在你的首个夜晚，你会得知两名玩家和一个外来者角色：这两名玩家之一是该角色（或者你会得知没有外来者在场）。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/librarian.png",
      "firstNightReminder": "唤醒图书管理员，对他指向两名玩家，并展示一个外来者角色标记。这两名玩家其中之一是这个外来者。",
      "otherNightReminder": "",
      "reminders": [
        "外来者",
        "错误",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="卖花女孩",
    updates={
      "ability": "每个夜晚*，你会得知在今天白天时是否有恶魔投过票。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/flowergirl.png",
      "firstNightReminder": "",
      "otherNightReminder": "对她点头或摇头来示意今天白天是否有恶魔投过票。",
      "reminders": [
        "恶魔已投票",
        "恶魔未投票",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="失忆者",
    updates={
      "ability": "你不知道你的能力是什么。每个白天你可以找说书人猜测一次，你会得知你的猜测有多准确。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/amnesiac.png",
      "firstNightReminder": "决定失忆者的能力，并根据具体能力决定是否需要唤醒失忆者、何时唤醒、唤醒后让他做出什么操作或得知什么信息。",
      "otherNightReminder": "如果失忆者的能力会让他在今晚醒来：唤醒他并执行其能力。",
      "reminders": [
        "？",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="修行者",
    updates={
      "ability": "在你的首个夜晚，你会得知距离最近的邪恶玩家位于你的顺时针还是逆时针方向。如果两侧的邪恶玩家与你距离相等，你得知的信息由说书人决定。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/shugenja.png",
      "firstNightReminder": "唤醒修行者，对他指向对应方向来告知他最近的邪恶玩家的方向。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "此即梦境。彼亦梦境。所见之物，非此即彼。",
    },
  ),
  townsfolk_fix(
    name="村夫",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：你会得知他的阵营。[+0~2村夫，复数村夫中有一人醉酒]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/village_idiot.png",
      "firstNightReminder": "唤醒村夫，让他指向一名玩家，用手势告诉他那名玩家的阵营。",
      "otherNightReminder": "唤醒村夫，让他指向一名玩家，用手势告诉他那名玩家的阵营。",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "玫瑰花是蓝色哒！草桂花是红色哒！哦豁，俺说反啦！",
    },
  ),
  townsfolk_fix(
    name="数学家",
    updates={
      "ability": "每个夜晚，你会得知有多少名玩家的能力因为其他角色的能力而未正常生效。（从上个黎明到你被唤醒时）",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/mathematician.png",
      "firstNightReminder": "给他展示数字手势来告诉他在首个夜晚里有多少玩家的角色能力受他人影响而未正常生效。",
      "otherNightReminder": "给他展示数字手势来告诉他从上个黎明到数学家醒来前有多少玩家的角色能力受他人影响而未正常生效。",
      "reminders": [
        "未正常生效",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "任何连续的，且能进行定量初等运算的形式系统X，都具有不完全性。也就是说，在这个形式系统X内存在一些命题，这些命题既不能被证明为真，也不能被证明为否。所以，你喝醉了。",
    },
  ),
  townsfolk_fix(
    name="送葬者",
    updates={
      "ability": "每个夜晚*，你会得知今天白天死于处决的玩家的角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/undertaker.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果有玩家今天白天死于处决，唤醒送葬者并对他展示那名玩家的角色标记。",
      "reminders": [
        "死于今日",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "嗯……看看我们发现了什么？左靴到足跟都有磨损，靴尖下还有些硝石屑。这是军人才会有的装束。",
    },
  ),
  townsfolk_fix(
    name="调查员",
    updates={
      "ability": "在你的首个夜晚，你会得知两名玩家和一个爪牙角色：这两名玩家之一是该角色（或者你会得知没有爪牙在场）。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/investigator.png",
      "firstNightReminder": "展示那个爪牙角色标记。指向被你标记“爪牙”和“错误”的两名玩家。",
      "otherNightReminder": "",
      "reminders": [
        "爪牙",
        "错误",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="守夜人",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择一名玩家：他会得知你是守夜人。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/nightwatchman.png",
      "firstNightReminder": "守夜人可以指向一名玩家。如果他这么做，则唤醒那名玩家，告知其被守夜人选中，且告知他守夜人是谁。",
      "otherNightReminder": "守夜人可以指向一名玩家。如果他这么做，则唤醒那名玩家，告知其被守夜人选中，且告知他守夜人是谁。",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "The night is cold and lonely, but I have the moon, the stars, the crisp wind and the soft thud of leather boots on cobbled stone for company. Yonder, candlelight flickers behind a murky window...",
    },
  ),
  townsfolk_fix(
    name="农夫",
    updates={
      "ability": "如果你在夜晚死亡，一名存活的善良玩家会变成农夫。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/farmer.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果农夫死于夜晚，唤醒一名存活的善良玩家告知他角色变化。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="猎手",
    updates={
      "ability": "每局游戏限一次，你可以在白天时公开选择一名玩家：如果他是恶魔，他死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/slayer.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="驱魔人",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家（与上个夜晚不同）：如果你选中了恶魔，他会得知你的角色，但他当晚不会因其自身能力而被唤醒。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/exorcist.png",
      "firstNightReminder": "",
      "otherNightReminder": "让驱魔人选择一名玩家，不能是上一夜他选择过的玩家。让驱魔人重新入睡。如果驱魔人选中了恶魔：唤醒恶魔。展示“该角色的能力对你生效”信息标记和驱魔人角色标记。指向驱魔人玩家。",
      "reminders": [
        "被选择",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "每一个不洁之灵，每一份撒旦之力，每一次炼狱敌人的猛袭，每一个军团，每一个崇拜恶魔的组织和教派，以我主耶稣基督的名义和力量，将你们驱逐。我命令你们，远离上帝的教堂，远离上帝按祂的形貌所创造并受神圣羔羊的宝血所救赎的灵魂。",
    },
  ),
  townsfolk_fix(
    name="茶艺师",
    updates={
      "ability": "如果与你邻近的两名存活的玩家是善良的，他们不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/tea_lady.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "不会死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "若你感到寒冷，茶能使你温暖。若你感到愤怒，茶能使你冷静。若你感到沮丧，茶能使你振奋。若你感到激动，茶能使你镇定。",
    },
  ),
  townsfolk_fix(
    name="女祭司",
    updates={
      "ability": "每个夜晚，你会得知一名说书人认为你最应该与其交流的玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/high_priestess.png",
      "firstNightReminder": "唤醒女祭司，指向一名玩家。让女祭司重新入睡。",
      "otherNightReminder": "唤醒女祭司，指向一名玩家。让女祭司重新入睡。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="镇长",
    updates={
      "ability": "如果只有三名玩家存活且白天没有人被处决，你的阵营获胜。如果你在夜晚死亡，可能会有一名其他玩家代替你死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/mayor.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="将军",
    updates={
      "ability": "每个夜晚，你会得知说书人认为哪个阵营当前更有优势（善良/邪恶/均势）。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/general.png",
      "firstNightReminder": "唤醒将军，对他用手势比划当前的优势阵营。",
      "otherNightReminder": "唤醒将军，对他用手势比划当前的优势阵营。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="贞洁者",
    updates={
      "ability": "当你首次被提名时，如果提名你的玩家是镇民，他立刻被处决。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/virgin.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="水手",
    updates={
      "ability": "每个夜晚，你要选择一名存活的玩家：你或他之一会醉酒直到下个黄昏。你不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/sailor.png",
      "firstNightReminder": "让水手选择一名存活玩家。标记那名玩家或水手醉酒。",
      "otherNightReminder": "让水手选择一名存活玩家。标记那名玩家或水手醉酒。",
      "reminders": [
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "你们随便谁来我都能把他喝到桌子底下去！说你呢！那个话痨！敢来和我喝一杯么？不来？那你呢，老太婆？你以前喝过老麦基利的加香料朗姆酒吗？保证能让你喝成个真男人！上船咯，噢耶！",
    },
  ),
  townsfolk_fix(
    name="杂耍艺人",
    updates={
      "ability": "在你的首个白天，你可以公开猜测任意玩家的角色最多五次。在当晚，你会得知猜测正确的角色数量。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/juggler.png",
      "firstNightReminder": "",
      "otherNightReminder": "给他展示数字手势来告诉他他当天白天猜测正确的次数。",
      "reminders": [
        "猜测正确",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "下一场表演，我需要一朵花、一袋豆子、一条玩具蛇、一支画笔、和一个电动的树篱修剪机。不过我得和你说，宝贝，这可能是我最后的表演了哦。",
    },
  ),
  townsfolk_fix(
    name="罂粟种植者",
    updates={
      "ability": "爪牙和恶魔互相不认识。如果你死亡，当晚他们会互相认识。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/poppy_grower.png",
      "firstNightReminder": "不要让恶魔和爪牙相认。",
      "otherNightReminder": "如果罂粟种植者死亡，安排恶魔和爪牙相认环节。",
      "reminders": [
        "唤醒邪恶",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="钟表匠",
    updates={
      "ability": "在你的首个夜晚，你会得知恶魔与爪牙之间最近的距离。（邻座的玩家距离为1）",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/clockmaker.png",
      "firstNightReminder": "给他展示数字手势来告诉他恶魔与爪牙之间最近的距离。",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="秉笔",
    updates={
      "ability": "如果你在白天死亡，当晚你会得知一名善良玩家。如果你在夜晚死亡，当晚你会得知一名邪恶玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/bingbi.png",
      "firstNightReminder": "",
      "otherNightReminder": "在夜晚时，如果秉笔旁放置了“死于今日”提示标记，唤醒秉笔。对他指向一名善良玩家。让秉笔重新入睡。移除“死于今日”提示标记。如果秉笔在夜晚死亡，唤醒秉笔。对他指向一名邪恶玩家。让秉笔重新入睡。",
      "reminders": [
        "死于今日",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "是非曲直，自在人心。",
    },
  ),
  townsfolk_fix(
    name="报丧女妖",
    updates={
      "ability": "如果恶魔杀死了你，所有玩家都会得知此事。从现在开始，你每天可以发起两次提名，每次投票时可以投两票。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/banshee.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果恶魔杀死了你，所有玩家都会得知此事。从现在开始，你每天可以发起两次提名，每次投票时可以投两票。",
      "reminders": [
        "具有能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="巡山人",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择一名存活的玩家：如果你选中了落难少女，她会变成一个不在场的镇民角色。[+落难少女]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/huntsman.png",
      "firstNightReminder": "唤醒巡山人，他可以摇头不使用能力，或选择一名玩家。如果巡山人选中了落难少女，则在巡山人入睡后通知落难少女角色变化。",
      "otherNightReminder": "如果巡山人未曾使用能力，唤醒巡山人，他可以摇头不使用能力，或选择一名玩家。如果巡山人选中了落难少女，则在巡山人入睡后通知落难少女角色变化。",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="变脸师",
    updates={
      "ability": "每个白天，如果你“疯狂”地证明自己是一个善良角色（与之前不同），你可能会在当晚获得那个角色的能力，直到下个黄昏。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/bianlianshi.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "疯狂",
      ],
      "remindersGlobal": [
        "是变脸师",
      ],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="赏金猎人",
    updates={
      "ability": "在你的首个夜晚，你会得知一名邪恶玩家。每当你得知的玩家死亡，你会在当晚得知另一名邪恶玩家。[会有一名镇民转变为邪恶阵营]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/bounty_hunter.png",
      "firstNightReminder": "指向一名邪恶玩家。随后唤醒那名因赏金猎人而转变为邪恶的镇民，并告知他变成了邪恶阵营。",
      "otherNightReminder": "如果赏金猎人知晓的邪恶玩家死亡，指向另一名邪恶玩家。",
      "reminders": [
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="戏法师",
    updates={
      "ability": "每个白天限一次，你可以公开猜测谁是爪牙，谁是恶魔。如果你猜对，善良阵营获胜。",
      "image": "https://clocktower-wiki.gstonegames.com/images/d/d6/Alsaahir.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "我在这里，因为你在这里；我在这里，所以你在这里。",
    },
  ),
  townsfolk_fix(
    name="传教士",
    updates={
      "ability": "每个夜晚，你要选择一名玩家：如果选中了爪牙，他会得知被传教士选中。所有被你选中的爪牙失去能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/preacher.png",
      "firstNightReminder": "传教士选择一名玩家。如果选中了爪牙，则唤醒并告知他被传教士选中。",
      "otherNightReminder": "传教士选择一名玩家。如果选中了爪牙，则唤醒并告知他被传教士选中。",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "富有和健康总比贫穷和疾病要好。",
    },
  ),
  townsfolk_fix(
    name="刀客",
    updates={
      "ability": "在你的首个夜晚，你会得知一个在场的爪牙角色。每局游戏限一次，你可以在白天公开选择一名玩家：如果他是你得知的角色，他死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/daoke.png",
      "firstNightReminder": "在首个夜晚，唤醒刀客，对他展示标记了“得知”的爪牙角色标记。",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="骑士",
    updates={
      "ability": "在你的首个夜晚，你会得知两名非恶魔玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/knight.png",
      "firstNightReminder": "唤醒骑士，对他指向两名非恶魔玩家。",
      "otherNightReminder": "",
      "reminders": [
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "当有人倒下时，他也就谋杀了世界上的某个部分。",
    },
  ),
  townsfolk_fix(
    name="教授",
    updates={
      "ability": "每局游戏限一次，在夜晚时*，你可以选择一名死亡的玩家：如果他是镇民，你会将他起死回生。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/professor.png",
      "firstNightReminder": "",
      "otherNightReminder": "教授可以选择一名死亡玩家。如果他这么做了，标记教授失去能力，然后如果那名玩家是镇民，标记那名玩家被复活。之后的夜晚无需再唤醒教授。",
      "reminders": [
        "复活",
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "过程很简单。将液压植入器连接到改良型气矩阵放大器上，加入20CC的伪多拉芬，让他的参数Z保持在20%以上，你丈夫就会重新活蹦乱跳。 现在，我们需要的仅仅是一次雷击。",
    },
  ),
  townsfolk_fix(
    name="魔术师",
    updates={
      "ability": "恶魔会以为你是爪牙。爪牙会以为你是恶魔。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/magician.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "1…2…唵嘛呢…3…4…叭咪吽…（嗖！）是的，正如你们所见，女士们先生们，梵斯沃船长的那袋金子不见了！没了！无迹可循！感谢诸位，晚安啦！",
    },
  ),
  townsfolk_fix(
    name="洗衣妇",
    updates={
      "ability": "在你的首个夜晚，你会得知两名玩家和一个镇民角色：这两名玩家之一是该角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/washerwoman.png",
      "firstNightReminder": "展示那个镇民角色标记。指向被你标记“镇民”和“错误”的两名玩家。",
      "otherNightReminder": "",
      "reminders": [
        "错误",
        "镇民",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="士兵",
    updates={
      "ability": "恶魔的负面能力对你无效。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/soldier.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="弄臣",
    updates={
      "ability": "当你首次将要死亡时，你不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fool.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "……然后国王说道：‘什么？！我甚至从未有过一条橡胶马裤，更别提一门奶油大炮了！’嗬嗬！欢乐一日！",
    },
  ),
  townsfolk_fix(
    name="悟道者",
    updates={
      "ability": "你以为你是一个外来者，但你实际上不是。如果有邪恶玩家的能力选择或影响了你，在该效果生效前你会变成一个不在场的镇民角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/wudaozhe.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [
        "是悟道者",
      ],
      "setup": 1,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="事务官",
    updates={
      "ability": "在你的首个夜晚，你会得知一名善良玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/steward.png",
      "firstNightReminder": "唤醒事务官，指向标记有“得知”的那名玩家。让事务官重新入睡。",
      "otherNightReminder": "",
      "reminders": [
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="店小二",
    updates={
      "ability": "在你的首个夜晚，你会得知两名善良玩家。他们之中会有一人醉酒，即使你已死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_8586487694761_0ecde168.jpg",
      "firstNightReminder": "唤醒店小二，对他指向标记有店小二的“熟客”和“醉酒”提示标记的这两名玩家。",
      "otherNightReminder": "",
      "reminders": [
        "熟客",
        "醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="引路人",
    updates={
      "ability": "每个夜晚，你要选择至多三名玩家：你会得知今晚是否有邪恶玩家的能力选择或影响了他们之中的玩家。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_2147287694761_01761fcb.jpg",
      "firstNightReminder": "唤醒引路人，让其选择至多三名玩家。以点头或摇头作为信息给出。",
      "otherNightReminder": "唤醒引路人，让其选择至多三名玩家。以点头或摇头作为信息给出。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "船篙点波心，跟着这篷船，避过暗礁浅涡，往前面渡头走。",
    },
  ),
  townsfolk_fix(
    name="无神论者",
    updates={
      "ability": "说书人可以打破游戏规则。如果说书人被处决，善良阵营获胜，即使你已死亡。[无邪恶角色在场]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/atheist.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="侍臣",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择一个角色：如果该角色在场，该角色之一从当晚开始醉酒三天三夜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/courtier.png",
      "firstNightReminder": "侍臣可以选择一个角色。如果他这么做了，标记侍臣失去能力，标记被选择的角色所对应的玩家醉酒。之后的夜晚无需再唤醒侍臣。",
      "otherNightReminder": "侍臣可以选择一个角色。如果他这么做了，标记侍臣失去能力，标记被选择的角色所对应的玩家醉酒。之后的夜晚无需再唤醒侍臣。",
      "reminders": [
        "失去能力",
        "醉酒1",
        "醉酒2",
        "醉酒3",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "比起一只羊带领的一百头狮子，我更害怕一头狮子带领的一百只羊。",
    },
  ),
  townsfolk_fix(
    name="史官",
    updates={
      "ability": "每个夜晚*，如果今天白天有玩家死于处决，你会得知存活镇民的数量。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/shiguan.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果今天白天有玩家死于处决，唤醒史官，告知其在场存活镇民数量。",
      "reminders": [
        "死于今日",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="和平主义者",
    updates={
      "ability": "被处决的善良玩家可能不会死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/pacifist.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="贤者",
    updates={
      "ability": "如果恶魔杀死了你，在当晚你会被唤醒并得知两名玩家，其中一名是杀死你的那个恶魔。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/role_icon/sage.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果恶魔杀死了贤者，唤醒贤者并指向两名玩家，其中一名玩家是杀死他的恶魔。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "这书山卷海中一定隐藏着秘密，我非常确信！这些秘密就隐藏在这一字一句之间等待着我们发掘。小子！再帮我多拿点蜡烛！还有墨水！虽然这些笔记有些晦涩，但有关恶魔的谜语很快就会被揭晓。",
    },
  ),
  townsfolk_fix(
    name="和尚",
    updates={
      "ability": "每个夜晚，当有邪恶玩家的能力首次选择或影响与你邻近的存活玩家时，改为此次能力不生效并持续至下个黎明，且你会得知你的能力被触发。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/heshang.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "已生效",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="吟游诗人",
    updates={
      "ability": "当一名爪牙死于处决时，除了你和旅行者以外的所有其他玩家醉酒直到明天黄昏。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/minstrel.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "全员醉酒",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="歌伶",
    updates={
      "ability": "每局游戏限一次，在白天时，你可以提议所有玩家观看你的演出，并从同意参加的玩家中选择你的观众。如果恶魔成为了观众，你会在当晚死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/geling.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果歌伶在白天使用了能力，且恶魔成为了观众，标记歌伶死亡。",
      "reminders": [
        "失去能力",
        "死亡",
        "观众",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="异教领袖",
    updates={
      "ability": "每个夜晚，你会转变为与你邻近的一名存活的玩家的阵营。每个白天，你可以提议所有玩家加入你的教派，如果所有善良玩家同意加入，你的阵营获胜。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/cult_leader.png",
      "firstNightReminder": "如果异教领袖改变了阵营，告诉他。",
      "otherNightReminder": "如果异教领袖改变了阵营，告诉他。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="杂技演员",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：如果当晚他醉酒或中毒，你死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/acrobat.png",
      "firstNightReminder": "",
      "otherNightReminder": "：唤醒杂技演员，让他选择一名玩家。如果当晚这名玩家醉酒或中毒，杂技演员死亡。",
      "reminders": [
        "死亡",
        "被选择",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "列位看官，请扶好帽盔，我将逆天而行，踏空起舞！身如飞燕，胆若雷霆，只为博君一笑一惊！",
    },
  ),
  townsfolk_fix(
    name="唱诗男孩",
    updates={
      "ability": "如果恶魔杀死了国王，你会得知哪名玩家是恶魔。[+国王]",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/choirboy.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果国王被恶魔杀死，将唱诗男孩唤醒并告诉他谁是那个杀死国王的恶魔。",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 1,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="方士",
    updates={
      "ability": "在你的首个夜晚，你要选择一个数字。在该数字对应的那一个夜晚，你会得知对应数量的在场角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_9290087694761_94c7b6f3.jpg",
      "firstNightReminder": "唤醒方士，让他选一个数字。如果他选择了1，给他展示一个在场角色。",
      "otherNightReminder": "在游戏的对应天数唤醒方士，给他展示对应数量的在场角色。",
      "reminders": [
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="风水师",
    updates={
      "ability": "在你的首个夜晚，你会得知一名玩家的角色类型。每个夜晚*，你会从他的顺时针方向得知下一名非旅行者玩家的角色类型。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/fengshuishi.png",
      "firstNightReminder": "唤醒风水师，告知他“得知”标记旁的玩家角色类型，并将标记顺时针移动一名玩家。",
      "otherNightReminder": "唤醒风水师，告知他“得知”标记旁的玩家角色类型，并将标记顺时针移动一名玩家。",
      "reminders": [
        "得知",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="驿使",
    updates={
      "ability": "每个白天，你可以公开声明一个角色。在当晚，你会得知该角色是否在场。如果你因此得知了否，你失去此能力。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/yishi.png",
      "firstNightReminder": "",
      "otherNightReminder": "如果驿使白天公开声明了一个角色，唤醒驿使：1.如果该角色在场，得知是；2.如果该角色不在场，得知否，并且驿使失去能力。",
      "reminders": [
        "在场",
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="锦衣卫",
    updates={
      "ability": "每个夜晚*，你要选择一名玩家：如果他在下个黄昏前死亡，你代替他死亡。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/upload/202301/c_5878087694761_691045fa.jpg",
      "firstNightReminder": "",
      "otherNightReminder": "移除上个夜晚放置的“保护”标记。唤醒锦衣卫，让其选择一名玩家。在该玩家角色标记旁放置“保护”提示标记。",
      "reminders": [
        "保护",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="工程师",
    updates={
      "ability": "每局游戏限一次，在夜晚时，你可以选择让恶魔变成你选择的恶魔角色，或让所有爪牙变成你选择的爪牙角色。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/role_icon/engineer.png",
      "firstNightReminder": "工程师选择不使用能力，或在剧本列表中选择恶魔或爪牙角色。如果他选择爪牙角色，则需要选择对应数量的爪牙。然后将这些玩家依次唤醒，并告知他们变成了什么角色。",
      "otherNightReminder": "工程师选择不使用能力，或在剧本列表中选择恶魔或爪牙角色。如果他选择爪牙角色，则需要选择对应数量的爪牙。然后将这些玩家依次唤醒，并告知他们变成了什么角色。",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="半仙",
    updates={
      "ability": "任何在夜晚使用自身能力选择你的其他玩家，会改为选中另一名邪恶玩家作为替代。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/banxian.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="公主",
    updates={
      "ability": "在你的首个白天，如果你提名并处决了一名玩家，当晚恶魔不会造成死亡。",
      "image": "https://clocktower-wiki.gstonegames.com/images/f/f2/Princess.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "不会死亡",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="宠妃",
    updates={
      "ability": "每局游戏限一次，说书人会在关于你的事情上打破规则。随后，你会秘密得知说书人为此做了什么。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/chongfei.png",
      "firstNightReminder": "",
      "otherNightReminder": "",
      "reminders": [
        "失去能力",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "",
    },
  ),
  townsfolk_fix(
    name="掮客",
    updates={
      "ability": "每个夜晚，你要选择两名存活玩家：如果他们阵营相同，今晚任何玩家使用自身能力选择他们之一作为目标时，改为选中另一名玩家。",
      "image": "https://clocktower-wiki.gstonegames.com/images/5/5b/Qianke.png",
      "firstNightReminder": "唤醒掮客，让他指向两名存活玩家。如果这两名玩家阵营相同，在这些玩家的角色标记旁放置“熟客”提示标记。",
      "otherNightReminder": "移除上个夜晚放置的“熟客”标记。唤醒车夫，让他指向两名存活玩家。如果这两名玩家阵营相同，在这些玩家的角色标记旁放置“熟客”提示标记。",
      "reminders": [
        "熟客",
      ],
      "remindersGlobal": [],
      "setup": 0,
      "flavor": "三教九流皆相识，稀有货、密讯、人脉不缺，报需求，价妥就成交。",
    },
  ),

  townsfolk_fix(
    name="半兽人",
    updates={
      "ability": "每个夜晚*，你要选择一名存活玩家：如果他是善良的，他死亡，并且当晚恶魔不会造成死亡。会有一名善良玩家始终被当作邪恶阵营。",
      "image": "https://oss.gstonegames.com/data_file/clocktower/web/icons/lycanthrope.png",
      "firstNightReminder": "",
      "otherNightReminder": "唤醒半兽人，让他选择一名玩家。如果该玩家是善良玩家，该玩家死亡，且当晚恶魔不会造成死亡。",
      "reminders": [
        "失足",
        "死亡"
      ],
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
