#!/usr/bin/env python3
"""Build source-confirmed scripts missing from the current Bilibili catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CHARACTER_ROOT = ROOT / "script_editor" / "public" / "characters"
TEAM_FOLDERS = {
  "townsfolk": "townsfolks",
  "outsider": "outsiders",
  "minion": "minions",
  "demon": "demons",
  "traveler": "travelers",
  "fabled": "fabled",
}


def first_variant(data: dict[str, Any], trait: str, default: Any) -> Any:
  values = data.get("variants", {}).get(trait, [])
  return values[0] if values else default


def character(name: str, team: str, **overrides: Any) -> dict[str, Any]:
  path = CHARACTER_ROOT / TEAM_FOLDERS[team] / f"{name}.json"
  data = json.loads(path.read_text(encoding="utf-8"))
  entry = {
    "id": name,
    "name": name,
    "edition": "custom",
    "team": team,
    "ability": first_variant(data, "ability", ""),
    "image": first_variant(data, "image", ""),
    "firstNight": first_variant(data, "firstNight", 0),
    "firstNightReminder": first_variant(data, "firstNightReminder", ""),
    "otherNight": first_variant(data, "otherNight", 0),
    "otherNightReminder": first_variant(data, "otherNightReminder", ""),
    "reminders": first_variant(data, "reminders", []),
    "remindersGlobal": first_variant(data, "remindersGlobal", []),
    "setup": first_variant(data, "setup", 0),
    "flavor": first_variant(data, "flavor", ""),
  }
  entry.update(overrides)
  return entry


def custom_character(name: str, team: str, **values: Any) -> dict[str, Any]:
  return {
    "id": name,
    "name": name,
    "edition": "custom",
    "team": team,
    "ability": values.get("ability", ""),
    "image": values.get("image", ""),
    "firstNight": values.get("firstNight", 0),
    "firstNightReminder": values.get("firstNightReminder", ""),
    "otherNight": values.get("otherNight", 0),
    "otherNightReminder": values.get("otherNightReminder", ""),
    "reminders": values.get("reminders", []),
    "remindersGlobal": values.get("remindersGlobal", []),
    "setup": values.get("setup", 0),
    "flavor": values.get("flavor", ""),
  }


def source_character(name: str, team: str, ability: str, **overrides: Any) -> dict[str, Any]:
  entry = character(name, team, ability=ability, **overrides)
  if entry["firstNight"]:
    entry["firstNightReminder"] = ability
  if entry["otherNight"]:
    entry["otherNightReminder"] = ability
  return entry


def jinx(name: str, ability: str, image: str) -> dict[str, Any]:
  return {
    "id": name,
    "name": name,
    "team": "jinx",
    "ability": ability,
    "image": image,
    "setup": 0,
  }


def note(text: str, html: str) -> dict[str, str]:
  return {"text": text, "html": html}


def write_script(path: Path, items: list[dict[str, Any]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  print(path.relative_to(ROOT))


def trial_by_ghost() -> list[dict[str, Any]]:
  icon_root = "/audit_icons/试胆大会"
  medium = character(
    "灵媒",
    "townsfolk",
    ability=(
      "在你的首个夜晚，你可以选择一个善良角色，然后后你会得知两名存活玩家："
      "其中一名玩家是这个角色。如果该角色不在场，这两名玩家中至少有一名是邪恶的。"
    ),
    firstNight=40,
    firstNightReminder=(
      "让灵媒选择一个善良角色。指向两名存活玩家，其中一名是该角色；"
      "如果该角色不在场，其中至少一名是邪恶的。"
    ),
    otherNight=0,
    otherNightReminder="",
    reminders=["善良角色", "存活玩家"],
  )
  return [
    {
      "id": "_meta",
      "name": "试胆大会",
      "author": "Lei的剧本钟楼",
    },
    character("小精灵", "townsfolk", firstNight=50),
    medium,
    character("共情者", "townsfolk", firstNight=60, otherNight=60),
    custom_character(
      "捉鬼专家",
      "townsfolk",
      ability="每个夜晚，如果与你邻近的存活玩家被选择，你会被唤醒。",
      image=f"{icon_root}/捉鬼专家.png",
      firstNight=10,
      firstNightReminder="如果与捉鬼专家邻近的存活玩家被选择，唤醒捉鬼专家。",
      otherNight=10,
      otherNightReminder="如果与捉鬼专家邻近的存活玩家被选择，唤醒捉鬼专家。",
      reminders=["被唤醒"],
    ),
    custom_character(
      "灵能侦探",
      "townsfolk",
      ability=(
        "每个夜晚*，你要选择一名玩家：你会得知他不是什么角色。"
        "如果他醉酒或中毒，改为得知他是什么角色。"
      ),
      image=f"{icon_root}/灵能侦探.png",
      otherNight=50,
      otherNightReminder=(
        "让灵能侦探选择一名玩家。如果他清醒且健康，展示一个不是其角色的角色标记；"
        "如果他醉酒或中毒，展示他的角色标记。"
      ),
      reminders=["选择"],
    ),
    character("博学者", "townsfolk"),
    custom_character(
      "摄影记者",
      "townsfolk",
      ability="每局游戏限一次，你公开选择一名玩家，他当晚不会因其自身能力被唤醒。",
      image=f"{icon_root}/摄影记者.png",
      reminders=["不会被唤醒", "已使用"],
    ),
    custom_character(
      "化身幽灵",
      "townsfolk",
      ability=(
        "你死亡后的每个白天，可以私下询问说书人，"
        "说书人会用手指在你的背上写下一个有关恶魔的字符。"
      ),
      image=f"{icon_root}/化身幽灵.png",
    ),
    character("酒鬼", "outsider"),
    custom_character(
      "捣蛋鬼",
      "outsider",
      ability="每个黎明，你转变为善良阵营；每个黄昏，你转变为邪恶阵营。",
      image=f"{icon_root}/捣蛋鬼.png",
      firstNight=90,
      firstNightReminder="在黎明，让捣蛋鬼转变为善良阵营；在黄昏，让他转变为邪恶阵营。",
      otherNight=90,
      otherNightReminder="在黎明，让捣蛋鬼转变为善良阵营；在黄昏，让他转变为邪恶阵营。",
    ),
    character("恐惧之灵", "minion", firstNight=20, otherNight=20),
    custom_character(
      "凶宅",
      "fabled",
      ability=(
        "每个夜晚，说书人可以选择一名存活玩家：他是邪恶的恶魔，"
        "与他邻近的两名存活玩家之一中毒，直到下次选择，"
        "上个被该能力选择的玩家会死亡。[-1恶魔，+1善良玩家]"
      ),
      image=f"{icon_root}/凶宅.png",
      firstNight=30,
      firstNightReminder=(
        "说书人可以选择一名存活玩家：他成为邪恶的恶魔，"
        "与他邻近的两名存活玩家之一中毒。"
      ),
      otherNight=30,
      otherNightReminder=(
        "说书人可以选择一名存活玩家：他成为邪恶的恶魔，"
        "与他邻近的两名存活玩家之一中毒，上个被该能力选择的玩家死亡。"
      ),
      reminders=["是恶魔", "中毒", "死亡"],
      setup=1,
    ),
  ]


def taotie_feast() -> list[dict[str, Any]]:
  teams = {
    "townsfolk": ["小精灵", "气球驾驶员", "送葬者", "舞蛇人", "哲学家", "变脸师"],
    "outsider": ["畸形秀演员", "解谜大师", "陌客", "异端分子"],
    "minion": ["提线木偶", "教父"],
    "demon": ["饕餮"],
  }
  entries = [
    {
      "id": "_meta",
      "name": "饕餮盛宴",
      "author": "清清Jungle",
      "notes": [
        note(
          "疯狂：当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力的证明某件事情，如不这么做会受到惩罚。",
          '<span style="color: rgb(103, 14, 171); font-weight: 900;">疯狂</span>：'
          '当你陷入“<span style="color: rgb(103, 14, 171); font-weight: 900;">疯狂</span>”时，意味着你需要向其他玩家'
          '<span style="color: rgb(14, 127, 207); font-weight: 900;">有诚意且努力</span>的证明某件事情，如不这么做会'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">受到惩罚</span>。',
        ),
        note(
          "中毒/醉酒：中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
          "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。醉酒同理。",
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒/醉酒</span>：'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家会失去能力，但会认为自己仍具有能力，'
          "说书人会做出这些玩家仍然具有能力的行为。如果"
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>玩家的角色能力会给他提供信息，说书人可能会给出'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">错误信息</span>，'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家不会得知自己'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>。'
          '<span style="color: rgb(143, 23, 1); font-weight: 900;">醉酒</span>同理。',
        ),
        note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚"),
      ],
    }
  ]
  for team, names in teams.items():
    entries.extend(character(name, team) for name in names)
  entries.append(jinx(
    "教父&异端分子",
    "异端分子会被教父当作一个不在场的外来者，异端分子会知道是哪个外来者。",
    entries[-2]["image"],
  ))
  return entries


def deadline_approaches() -> list[dict[str, Any]]:
  teams = {
    "townsfolk": ["洗衣妇", "图书管理员", "祖母", "舞蛇人", "半兽人", "博学者", "守夜人", "食人族"],
    "outsider": ["酒鬼", "解谜大师"],
    "minion": ["限", "科学怪人"],
    "demon": ["利维坦", "暴乱"],
  }
  entries = [{"id": "_meta", "name": "大限将至", "author": "清清Jungle"}]
  for team, names in teams.items():
    entries.extend(character(name, team) for name in names)
  image_by_name = {entry["name"]: entry["image"] for entry in entries[1:]}
  entries.extend([
    jinx(
      "科学怪人&酒鬼",
      "如果恶魔拥有酒鬼的能力，改为由科学怪人选择一名玩家：如果他是镇民，他醉酒。",
      image_by_name["科学怪人"],
    ),
    jinx(
      "利维坦&祖母",
      "如果利维坦在场，孙子死于处决，祖母会一同死亡。",
      image_by_name["利维坦"],
    ),
    jinx(
      "暴乱&祖母",
      "如果暴乱在场，孙子在白天死亡，祖母会一同死亡。",
      image_by_name["暴乱"],
    ),
  ])
  return entries


def orletis_manor() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("冒险家", "在你的首个夜晚，你会得知两个数字。有且仅有一名邪恶玩家与你的最近初始距离在这两个数字之间（邻座算1，不含这两个数字）。或你会得知无法获取合规信息。"),
      ("小女孩", "在你的首个夜晚，你要选择一名玩家，你即将死亡时，如果他存活，他代替你死亡。"),
      ("先知", "在你的首个夜晚，你会得知一个在场的邪恶阵营角色。每局游戏限一次：晚上，你可以选择一名玩家，该玩家不会被该角色能力影响直到下个黄昏。"),
      ("医生", "每个夜晚，你会得知自己是否中毒或醉酒，此能力不会受到中毒或醉酒的影响。然后你要选择一名角色：他解除醉酒并恢复健康且无法陷入中毒或醉酒直到下个黄昏。"),
      ("律师", "每个夜晚，你要选择一名非律师的角色。当你选择的角色在场状态和以往选择过的不同，你死亡。"),
      ("哭泣小丑", "每个夜晚，你要选择一名除你以外的玩家。当你死亡后，你会在当晚依次得知每一个你选择过的玩家和你第一次选择的玩家阵营是否相同。"),
      ("机械师", "每个夜晚，你要选择三名玩家：你会得知这三名玩家有多少角色类型，但是你有可能获得一次错误信息。在你死亡后，你会得知你一共获得过多少错误信息。"),
      ("病患", "每个夜晚，你要选择一名玩家，你会得知该玩家的角色性别。（医生，机械师，小女孩，心理学家，拉拉队员，古董商，调酒师，盲女，梦之女巫，红蝶，使徒为女，其余角色为男）"),
      ("心理学家", "首个夜晚，你会得知病患是谁（或你会得知没有病患在场）。每个夜晚*，你可以选择一名已死亡的玩家：如果他不是恶魔，他复活，然后你死亡。"),
      ("拉拉队员", "每局游戏限一次，晚上，你可以选择一名其他存活玩家：他会被唤醒，如果他夜晚行动会再次行动。（限次技能不刷新）"),
      ("逃脱大师", "每局游戏限一次，当你在晚上即将被恶魔杀死，你不会死亡，且所有玩家会得知此事。然后尝试杀死你的玩家会再次行动。"),
      ("古董商", "每局游戏限一次，晚上，你可以选择一名非恶魔角色，他醉酒一天两夜。如果该角色不在场，你死亡。"),
      ("佣兵", "当你在晚上即将死亡，你不会死亡且你会得知此事，下个夜晚，你死亡，即使因为任何原因使你不会死亡。"),
    ],
    "outsider": [
      ("调酒师", "每个晚上，你要选择一名除你以外的其他未被你选择过的存活玩家：他在下个黄昏前不会死亡，如果他是善良的，他醉酒。若你选中了小女孩，盲女，或拉拉队员，改为无事发生（既不会免疫死亡也不会醉酒）。你死亡后，说书人可以使用一次你的能力。"),
      ("盲女", "当你得知你死亡后，一名镇民玩家会在下个夜晚死亡。"),
      ("幸运儿", "你以为你是一个不在场的镇民角色，但其实你不是。每局游戏限一次，任意善良玩家可以公开猜测自己是幸运儿，如果猜对，你会变成认知的角色。"),
      ("木偶师", "在你的首个夜晚，你死亡，但是会被当作存活。"),
    ],
    "minion": [
      ("摄影师", "每局游戏限一次：晚上，你可以拍照，直到下个黄昏：所有新死亡的玩家仍存活但被当作死亡，所有复活的玩家死亡但会被当作存活。因你造成的假死或活尸状态不会因为任何原因被移除。（包括但不限于你死亡，变成别的角色，中毒和醉酒）"),
      ("梦之女巫", "每个夜晚，你要选择一名玩家：如果他是善良的，他被寄生。被寄生的玩家不计入邪恶阵营获胜条件。被寄生的人会得知自己被寄生。"),
      ("宿伞白魂", "与你附近的镇民中毒。如果宿伞黑魂死亡时大于等于五人在场，你会被视为恶魔并且每个夜晚，你要选择一名玩家：他死亡。如果多于一名宿伞白魂在场，由说书人决定谁会被视为恶魔。"),
      ("噩梦", "每个夜晚，你要选择一名玩家：你得知他的角色。每局游戏限一次：晚上*，你可以让今晚得知的玩家角色变成你指定的一个非恶魔角色。"),
    ],
    "demon": [
      ("红蝶", "每个夜晚*，你要选择一名玩家：他死亡，如果选择的是存活玩家，你失去你后半段技能直到下个黎明。你可能会被善良阵营的能力当作善良阵营，镇民角色，外来者角色。"),
      ("厂长", "每个夜晚*，你要选择一名玩家：他死亡。你死亡后，所有善良玩家中毒直到下个黄昏（假死无效）。[+宿伞白魂]"),
      ("使徒", "每个夜晚*，你要选择一名玩家，他中毒并死亡。然后该玩家对坐的一名玩家会中毒直到下个黄昏。"),
      ("宿伞黑魂", "每个夜晚*，你要选择一名玩家：他死亡，然后你可以和说书人猜拳，若你赢，你要选择一名玩家：他死亡。"),
    ],
  }
  first_order = {
    name: (index + 1) * 10
    for index, name in enumerate([
      "调酒师", "医生", "心理学家", "噩梦", "先知", "小女孩", "木偶师", "病患",
      "律师", "梦之女巫", "冒险家", "逃脱大师", "古董商", "拉拉队员", "佣兵",
      "机械师", "哭泣小丑",
    ])
  }
  other_order = {
    name: (index + 1) * 10
    for index, name in enumerate([
      "调酒师", "医生", "心理学家", "噩梦", "先知", "摄影师", "律师", "盲女",
      "宿伞白魂", "红蝶", "厂长", "使徒", "宿伞黑魂", "古董商", "梦之女巫",
      "逃脱大师", "佣兵", "病患", "机械师", "拉拉队员", "哭泣小丑",
    ])
  }
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "欧利蒂丝庄园",
    "author": "临雨",
    "notes": [
      note(
        "可能：某件事“可能”发生，代表说书人决定该事情是否发生。",
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">可能</span>：某件事“'
        '<span style="color: rgb(103, 14, 171); font-weight: 900;">可能</span>”发生，代表说书人决定该事情是否发生。',
      ),
      note(
        "中毒/醉酒：中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。"
        "如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。醉酒同理。",
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒/醉酒</span>：'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家会失去能力，但会认为自己仍具有能力，'
        "说书人会做出这些玩家仍然具有能力的行为。如果"
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>玩家的角色能力会给他提供信息，说书人可能会给出'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">错误信息</span>，'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家不会得知自己'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>。'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">醉酒</span>同理。',
      ),
      note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚"),
    ],
  }]
  for team, team_roles in roles.items():
    for name, ability in team_roles:
      values: dict[str, Any] = {
        "ability": ability,
        "image": f"/audit_icons/欧利蒂丝庄园/{name}.png",
        "setup": 1 if name == "厂长" else 0,
      }
      if name in first_order:
        values.update(firstNight=first_order[name], firstNightReminder=ability)
      if name in other_order:
        values.update(otherNight=other_order[name], otherNightReminder=ability)
      entries.append(custom_character(name, team, **values))
  entries.append(jinx(
    "摄影师&宿伞白魂",
    "因摄影师的能力而造成的假死宿伞黑魂不会让宿伞白魂视为恶魔，当宿伞黑魂真正死亡时，宿伞白魂才会被唤醒。",
    "/audit_icons/欧利蒂丝庄园/摄影师.png",
  ))
  return entries


def devotees_two() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("刀客", "在你的首个夜晚，你得知一个在场的爪牙角色。每局游戏限一次，你可以在白天公开选择一名玩家：如果他是你得知的角色，他死亡。"),
      ("修行者", "在你的首个夜晚，你会得知距离最近的邪恶玩家位于你的顺时针还是逆时针方向。如果两侧的邪恶玩家与你距离相等，你得知的信息由说书人决定。"),
      ("小精灵", "在你的首个夜晚，你会得知一个在场的镇民角色。如果你“疯狂”地证明你是该角色，当他死亡时你获得该角色的能力。"),
      ("郎中", "每个夜晚，你要选择一名除你和旅行者以外的玩家：你会得知一个与他能力相关的词语。"),
      ("牧师", "每个夜晚，你要选择两名玩家：你会得知他们均不属于哪个角色类型。"),
      ("卖花女孩", "每个夜晚*，你会得知在今天白天时是否有恶魔投过票。"),
      ("神谕者", "每个夜晚*，你会得知有多少名死亡的玩家是邪恶的。"),
      ("博学者", "每个白天，你可以私下询问说书人以得知两条信息：一个是正确的，一个是错误的。"),
      ("画像师", "每个白天，你可以公开选择一名玩家：当晚你会得知他今天白天是否“疯狂”地证明自己的角色和所获得的信息。"),
      ("艺术家", "每局游戏限一次，在白天时，你可以私下拜访说书人提问一个是非题，你会得到该问题的答案（是/不是/我不知道）。"),
      ("病患", "每局游戏限一次，你会被唤醒：你每有一个夜晚未被唤醒，就会获得一个在场角色的能力。"),
      ("不信教者", "如果恶魔杀死了你，他会转变为善良阵营，但他不知道。"),
      ("秉笔", "如果你在白天死亡，当晚你会得知一名善良玩家。如果你在夜晚死亡，当晚你会得知一名邪恶玩家。"),
    ],
    "outsider": [
      ("酒保", "与你邻近的善良玩家之一醉酒，即使你已死亡。"),
      ("弃徒", "你不知道你是弃徒，你会以为自己是一个在场的镇民角色，但其实你不是。对调你自身的胜负结果，除非你提名并处决了与你认知角色相同的玩家，即使你已死亡。"),
      ("落难少女", "所有爪牙都知道落难少女在场。每局游戏限一次，任意爪牙可以公开猜测你是落难少女，如果猜对，你的阵营落败。"),
      ("食人魔", "在你的首个夜晚，你要选择一名除你以外的玩家：你转变为他的阵营，即使你醉酒或中毒，但你不知道你转变后的阵营。"),
    ],
    "minion": [
      ("吸血鬼", "你知道一些善良玩家和他们的角色。[这些玩家失去能力并以为自己是爪牙]"),
      ("哥布林", "如果你在被提名后公开声明自己是哥布林且在那个白天被处决，你的阵营获胜。"),
      ("死魂灵", "在你的首个夜晚，你死亡，但依然被当作存活。如果你再次死亡，与你邻近的存活镇民之一获得你的能力，即使你已死亡。"),
      ("红唇女郎", "如果大于等于五名玩家存活时（旅行者不计算在内）恶魔死亡，你变成那个恶魔。"),
    ],
    "demon": [
      ("奇奇默克", "每个夜晚*，你要选择一名玩家：他死亡。距离你最近的爪牙与你之间的镇民玩家能力都会产生错误信息。"),
      ("方古", "每个夜晚*，你要选择一名玩家：他死亡。被该能力杀死的外来者改为变成邪恶的方古且你代替他死亡，但每局游戏仅能成功转化一次。[+1外来者]"),
      ("军团", "每个夜晚*，可能有一名玩家死亡。如果一项提名只有邪恶玩家投票，投票无效。你也会被当作是爪牙。[半数以上玩家为军团]"),
      ("涡流", "每个夜晚*，你要选择一名玩家：他死亡。镇民玩家的能力都会产生错误信息。如果白天没人被处决，邪恶阵营获胜。"),
    ],
    "fabled": [
      ("圣洁之魂", "游戏过程中邪恶玩家的总数最多能比初始设置多一名。"),
      ("独奏家", "旅行者会被非旅行者角色当作不在游戏中，但恶魔仍然可以选择杀死旅行者。"),
    ],
  }
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "效死之徒Ⅱ",
    "author": "摸鱼学徒",
    "notes": [note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚")],
  }]
  for team, team_roles in roles.items():
    for name, ability in team_roles:
      overrides = {"image": "/audit_icons/效死之徒Ⅱ/病患.png"} if name == "病患" else {}
      entries.append(source_character(name, team, ability, **overrides))
  image_by_name = {entry["name"]: entry["image"] for entry in entries[1:]}
  entries.append(jinx(
    "方古&红唇女郎",
    "如果方古成功转化了外来者并因此死去，红唇女郎不会变成方古。",
    image_by_name["方古"],
  ))
  return entries


def return_before_march() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("调查员", "在你的首个夜晚，你会得知两名玩家和一个爪牙角色：这两名玩家之一是该角色。（或者你会得知没有爪牙在场）"),
      ("共情者", "每个夜晚，你会得知与你邻近的两名存活的玩家中邪恶玩家的数量。"),
      ("气球驾驶员", "每个夜晚，你会得知一名与上个夜晚得知的玩家角色类型不同的玩家。[+0~1外来者]"),
      ("驱魔人", "每个夜晚*，你要选择一名玩家（与上个夜晚不同）：如果你选中了恶魔，他会得知你是驱魔人，但他当晚不会因其自身能力而被唤醒。"),
      ("工程师", "每局游戏限一次，在夜晚时，你可以选择让恶魔变成你选择的恶魔角色，或让所有爪牙变成你选择的爪牙角色。"),
      ("巡山人", "每局游戏限一次，在夜晚时，你可以选择一名存活的玩家：如果你选中了落难少女，她会变成一个不在场的镇民角色。[+落难少女]"),
      ("杂耍艺人", "在你的首个白天，你可以公开猜测任意玩家的角色最多五次。在当晚，你会得知猜测正确的角色数量。"),
      ("艺术家", "每局游戏限一次，在白天时，你可以私下拜访说书人提问一个是非题，你会得到该问题的答案（是/不是/我不知道）。"),
      ("造谣者", "每个白天，你可以公开发表一个声明。如果该声明正确，在当晚会有一名玩家死亡。"),
      ("博学者", "每个白天，你可以私下拜访说书人获得两条信息：一个是正确的，一个是错误的。"),
      ("炼金术士", "你拥有一个爪牙角色的能力。当你使用能力时，说书人可能会要求你更换选择。"),
      ("弄臣", "当你首次将要死亡时，你不会死亡。"),
      ("镇长", "如果只有三名玩家存活且白天没有人被处决，你的阵营获胜。如果你在夜晚即将死亡，可能会有一名其他玩家代替你死亡。"),
    ],
    "outsider": [
      ("莽夫", "每个夜晚，首个使用其自身能力选择了你的玩家会醉酒直到下个黄昏。你会转变为他的阵营。"),
      ("落难少女", "所有爪牙都知道落难少女在场。每局游戏限一次，任意爪牙可以公开猜测你是落难少女，如果猜对，你的阵营落败。"),
      ("解谜大师", "一名玩家醉酒，即使你已死亡。每局游戏限一次，你可以猜测谁是那个醉酒的玩家，如果猜对了，你会得知谁是恶魔，但如果猜错了，你会得知错误的“谁是恶魔”信息。"),
      ("帽匠", "如果你死亡，当晚爪牙和恶魔玩家可以选择变成新的爪牙和恶魔角色。"),
    ],
    "minion": [
      ("巫师", "每局游戏限一次，你可以向说书人许愿。如果愿望被实现，可能会伴随着代价和线索。"),
      ("麻脸巫婆", "每个夜晚*，你要选择一名玩家和一个角色，如果该角色不在场，他要变成该角色。如果因此创造了一个恶魔，当晚的死亡由说书人决定。"),
      ("投毒者", "每个夜晚，你要选择一名玩家：他在当晚和明天白天中毒。"),
      ("召唤师", "在首个夜晚，你会得知三个伪装。在第三个夜晚，你要选择一名玩家：他变成由你选择的邪恶恶魔。[无恶魔在场]"),
    ],
    "demon": [
      ("珀", "每个夜晚*，你可以选择一名玩家：他死亡。如果你上次选择时没有选择任何玩家，当晚你要选择三名玩家：他们死亡。"),
      ("沙巴洛斯", "每个夜晚*，你要选择两名玩家：他们死亡。你上个夜晚选择过且当前死亡的玩家之一可能会被你反刍。"),
      ("哈迪寂亚", "每个夜晚*，你可以选择三名玩家（所有玩家都会得知你选了谁）：他们分别秘密决定自己的生死，然后如果他们都存活则都死亡。"),
      ("暴乱", "在第三个白天，所有爪牙会变成暴乱，当天被提名的玩家会立即死亡且必须再次提名一名存活的玩家。"),
    ],
    "fabled": [
      ("圣洁之魂", "游戏过程中邪恶玩家的总数最多能比初始设置多一名。"),
      ("哨兵", "在初始设置时，可能会额外增加或减少一个外来者。"),
      ("私货商人", "如真似幻：在第三个白天，如果暴乱醉酒或中毒，则爪牙不会变成暴乱。但是当天被提名的玩家依然会立即死亡且必须再次提名一名存活的玩家。"),
    ],
  }
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "回到三月之前",
    "author": "星火乐",
    "notes": [note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚")],
  }]
  for team, team_roles in roles.items():
    entries.extend(source_character(name, team, ability) for name, ability in team_roles)
  image_by_name = {entry["name"]: entry["image"] for entry in entries[1:]}
  entries.extend([
    jinx(
      "驱魔人&暴乱",
      "如果驱魔人在第三个夜晚选中了暴乱，爪牙不会变成暴乱。",
      image_by_name["驱魔人"],
    ),
    jinx(
      "炼金术士&召唤师",
      "如果炼金术士获得了召唤师的能力，游戏会以初始有恶魔在场进行。炼金术士召唤师选择的玩家会变成恶魔但不会改变阵营。",
      image_by_name["炼金术士"],
    ),
    jinx(
      "镇长&暴乱",
      "镇长可以停止提名。如果他这样做了，并且场上只有一名暴乱存活，善良阵营获胜；否则，邪恶阵营获胜。",
      image_by_name["镇长"],
    ),
    jinx(
      "麻脸巫婆&落难少女",
      "如果麻脸巫婆创造了落难少女，改为由说书人来决定哪一名玩家变成落难少女。",
      image_by_name["麻脸巫婆"],
    ),
    jinx(
      "召唤师",
      "召唤师无法创造已经在场的恶魔。如果召唤师创造了一名不在场的恶魔，当晚的死亡由说书人决定。",
      image_by_name["召唤师"],
    ),
    jinx(
      "召唤师&工程师",
      "如果工程师的能力使得召唤师在使用自己的能力前离场，召唤师会在此前立即使用自己的能力。",
      image_by_name["召唤师"],
    ),
  ])
  return entries


def favonius_mystery_v15() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("安柏", "在你的首个夜晚，你要选择尘世执政、执行官、爪牙或外来者各一名：你会得知那些角色中有多少角色在场。如果你选择的角色都不在场，你获得错误资讯。"),
      ("米卡", "在你的首个夜晚，你会得知离你最远的外来者之间的最近距离。（邻座的玩家距离为1）"),
      ("九条裟罗", "在你的首个夜晚，你要选择与初始爪牙数量+1的玩家：你会得知那些玩家中有多少镇民。"),
      ("莫娜", "每个夜晚，你要选择一位除你以外的非旅行者玩家：你会得知两个角色，该玩家是其中一个角色。"),
      ("八重神子", "每个夜晚，你要选择一名玩家：你得知他是否是尘世执政或执行官。"),
      ("温迪", "你是尘世执政。每个夜晚，你要选择一名玩家和角色：你会得知他在本局游戏中是否被你选择的角色的能力选择或影响。"),
      ("纳西妲", "你是尘世执政。每个夜晚，你要选择两名玩家：你得知他是否为外来者。如果你死于夜晚，被你选择的外来者失去能力。[+0~1外来者]"),
      ("优菈", "每个夜晚*，你要选择一名除你以外在今天白天发起提名的玩家：你得知他与被提名的玩家阵营是否相同。会有一名善良玩家被镇民视为邪恶阵营、爪牙角色或恶魔角色。"),
      ("胡桃", "每个夜晚*，如果白天有玩家死于处决：你得知与被处决玩家与最近的邪恶玩家之间的距离；如果死于处决的玩家是尘世执政，你改为得知那名邪恶玩家的角色。如果被处决的玩家是邪恶玩家，你会得知错误讯息。（邻座的玩家距离为1）"),
      ("钟离", "你是尘世执政。每个夜晚*，你要选择一名存活玩家（与上个夜晚不同），他在当晚不会因为邪恶阵营的能力死亡。"),
      ("琴", "每个夜晚*，你会得知今天白天有多少旅行者外的角色类别发起了提名。"),
      ("迪卢克", "每个夜晚*，你可以选择一名除你以外的玩家和角色（都与之前不同）：如果他是那个角色且不是执行官，他死亡且恶魔得知你在场。"),
      ("雷电将军", "你是尘世执政。每局游戏限一次，当你发起提名时，你可以公开声称你是雷电将军并说出「此刻，寂灭之时！」，随后，如果被你提名的玩家是邪恶的，他被处决。"),
    ],
    "outsider": [
      ("流浪者", "你与恶魔互相得知彼此在场。每局游戏限一次，恶魔可以拜访说书人并猜测你是流浪者：如果猜测正确，会有一名善良玩家在下个白天开始时被处决，即使你已死亡。"),
      ("北斗", "在你的首个夜晚，你得知一名不在场的爪牙角色。如果你死亡：当晚恶魔获得那名不在场爪牙的能力。"),
      ("芙宁娜", "当邪恶阵营落败时，场上存活（旅行者不计算在内）玩家大于等于五名的场合，说书人会宣布芙宁娜在场。在一分钟内，邪恶玩家要猜测谁是芙宁娜并指向一名玩家，如果所有邪恶玩家都猜测你，善良阵营落败。即使你死于处决。"),
      ("七七", "如果你死亡，恶魔会得知此事，明天首个被提名的存活的玩家不会被计算在胜利条件内。"),
    ],
    "minion": [
      ("债务处理人", "每局游戏限一次，当你发起提名时，你可以公开声称你是债务处理人，并喊出：“偿债吧！”，随后，如果被你提名的玩家不是尘世执政，他被处决。"),
      ("雷萤术士", "在你的首个夜晚，你要选择一个数字：黄昏时，如果白天的提名次数首次大于等于选择的数字，会有与该数字相同数量的玩家中毒直到下个黄昏。"),
      ("渊上之物", "如果大于等于五名玩家存活时（旅行者除外）恶魔不因自身能力而死亡，一名提名过邪恶玩家的镇民会变成那个邪恶的恶魔，但每局游戏仅能成功转化一次。[只有一名外来者]"),
      ("藏镜仕女", "每个夜晚*，你要选择一名存活的玩家（需与上一晚不同）：当晚首个通过自身能力选择该玩家的玩家改为选择自己并死亡。[+1外来者]"),
    ],
    "demon": [
      ("冰之女皇", "你是尘世执政。每个夜晚*，你要选择一名玩家：他死亡。如果所有爪牙死亡，之后每个夜晚你行动两次。"),
      ("散兵", "你是执行官。每个夜晚*，你要选择一名玩家：他死亡。如果场上没有存活的尘世执政，邪恶阵营获胜。[半数的镇民是善良的尘世执政（向下或向上取整）、无流浪者]"),
      ("博士", "你是执行官。每个夜晚*，你要选择一名玩家：他死亡；那之后，一名与死亡玩家邻近的存活的善良玩家中毒直到下个黄昏。"),
      ("女士", "你是执行官。每个夜晚*，你要选择两名玩家：第一个被选中的玩家死亡；另一名得知你在场。如果任意存活玩家“疯狂”地证明女士在场：一名被你选择过的存活玩家可能被处决，且其他被你选择过的存活玩家一同死亡。"),
    ],
  }
  first_order = {
    "尘世执政": 8,
    "雷萤术士": 10,
    "莫娜": 20,
    "米卡": 30,
    "温迪": 40,
    "八重神子": 50,
    "纳西妲": 60,
    "北斗": 70,
    "九条裟罗": 80,
    "安柏": 90,
    "流浪者": 100,
  }
  other_order = {
    "雷萤术士": 10,
    "渊上之物": 20,
    "债务处理人": 30,
    "芙宁娜": 40,
    "迪卢克": 50,
    "藏镜仕女": 60,
    "钟离": 70,
    "博士": 80,
    "女士": 90,
    "冰之女皇": 100,
    "散兵": 110,
    "北斗": 120,
    "七七": 130,
    "优菈": 140,
    "胡桃": 150,
    "纳西妲": 160,
    "莫娜": 170,
    "八重神子": 180,
    "琴": 190,
    "温迪": 200,
  }
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "西风谜团",
    "author": "R6lover",
    "notes": [
      note(
        "疯狂：当你陷入“疯狂”时，意味着你需要向其他玩家有诚意且努力的证明某件事情，如不这么做会受到惩罚。",
        '<span style="color: rgb(103, 14, 171); font-weight: 900;">疯狂</span>：'
        '当你陷入“<span style="color: rgb(103, 14, 171); font-weight: 900;">疯狂</span>”时，意味着你需要向其他玩家'
        '<span style="color: rgb(14, 127, 207); font-weight: 900;">有诚意且努力</span>的证明某件事情，如不这么做会'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">受到惩罚</span>。',
      ),
      note(
        "中毒/醉酒：中毒的玩家会失去能力，但会认为自己仍具有能力，说书人会做出这些玩家仍然具有能力的行为。如果中毒玩家的角色能力会给他提供信息，说书人可能会给出错误信息，中毒的玩家不会得知自己中毒。醉酒同理。",
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒/醉酒</span>：'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家会失去能力，但会认为自己仍具有能力，'
        "说书人会做出这些玩家仍然具有能力的行为。如果"
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>玩家的角色能力会给他提供信息，说书人可能会给出'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">错误信息</span>，'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>的玩家不会得知自己'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">中毒</span>。'
        '<span style="color: rgb(143, 23, 1); font-weight: 900;">醉酒</span>同理。',
      ),
      note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚"),
    ],
  }]
  icon_root = "/audit_icons/西风谜团"
  for team, team_roles in roles.items():
    for name, ability in team_roles:
      values: dict[str, Any] = {
        "image": f"{icon_root}/{name}.png",
        "firstNight": first_order.get(name, 0),
        "otherNight": other_order.get(name, 0),
      }
      if name == "九条裟罗":
        values.update(
          firstNightReminder=ability,
          reminders=[],
          remindersGlobal=[],
        )
        entries.append(custom_character(name, team, ability=ability, **values))
      else:
        entries.append(source_character(name, team, ability, **values))
  entries.extend([
    custom_character(
      "尘世执政",
      "fabled",
      ability="温迪、钟离、雷电将军、纳西妲和冰之女皇是尘世执政。[至少有一名尘世执政在场]",
      image=f"{icon_root}/尘世执政.png",
      firstNight=first_order["尘世执政"],
      firstNightReminder="确认至少有一名尘世执政在场。",
      setup=1,
    ),
    custom_character(
      "执行官",
      "fabled",
      ability="女士、散兵、博士是执行官。",
      image=f"{icon_root}/执行官.png",
    ),
    jinx(
      "渊上之物&北斗",
      "如果北斗死亡且恶魔会因此获得渊上之物的能力，改为一名存活的爪牙玩家获得此能力，且他会得知此事。",
      f"{icon_root}/渊上之物.png",
    ),
  ])
  return entries


def wei_mu_xuan_xi() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("出马仙", "在你的首个夜晚，你得知五个不在场角色。"),
      ("念空和尚", "在你的首个夜晚，你得知一个在场的恶魔角色。"),
      ("风水学徒", "在你的首个夜晚，你得知两名玩家，其中一名玩家与邪恶玩家的距离最近。"),
      ("“鲁班”", "每个夜晚，你可以选择一名玩家。你得知他角色的字数。（不包括标点符号）"),
      ("奇门遁甲", "每个夜晚，你要选择一名玩家，你得知他对本局游戏的影响程度。（微小/普通/重大）"),
      (
        "断命师",
        "每个夜晚，你可以选择一名玩家。下个白天提名开始时，所有玩家得知断命师提名他，"
        "本次提名没有辩解环节直接投票（断命师提名并投票了xx）。每局游戏限一次，在白天时，"
        "恶魔可以私下拜访说书人猜测谁是断命师，如果猜对，你当晚死亡。",
      ),
      (
        "符士",
        "每个夜晚，你要选择一名存活玩家。被你选择过的邪恶玩家本局游戏无法使用投票标记，"
        "即使你已死亡。",
      ),
      (
        "赶尸匠",
        "你无法使用投票标记。每个夜晚*，你可以选择一名拥有投票标记的死亡玩家："
        "你获得他的能力直到下个黄昏且他失去投票标记。",
      ),
      (
        "扶乩",
        "每个夜晚*，你可以选择一名玩家，你得知当晚有多少名除你以外的玩家发动自身能力选中他。",
      ),
      ("天师", "每个夜晚*，你可以得知距离新的死亡玩家最近的邪恶玩家的角色类型。"),
      ("唯物主义", "当你死在夜晚时，一名与你距离最近的邪恶玩家之一投票计数减一。"),
      (
        "巫傩",
        "你知晓本局游戏的传奇角色。每局游戏限一次，在白天时，你可以私下拜访说书人选择一个"
        "不在场的传奇角色，传奇角色变为该角色。",
      ),
      (
        "失忆者",
        "你不知道你的能力是什么。每个白天你可以找说书人猜测一次，你会得知你的猜测有多准确。"
        "（无关/有关/接近/完美）",
      ),
    ],
    "outsider": [
      (
        "冥婚媒",
        "当首次有玩家死于处决时，当晚你要选择一名除你以外的存活玩家。如果他是善良的，他开始醉酒。",
      ),
      (
        "阴童子",
        "当你死于处决时，如果提名你的玩家是善良的，对你的提名没有投票的善良玩家会开始醉酒。"
        "如果你“疯狂”的证明你是外来者，恶魔当晚选择一位善良玩家中毒。",
      ),
      (
        "江湖骗子",
        "每个夜晚，说书人会给你一条错误的信息，你要“疯狂”地证明该信息是正确的，否则你可能会被处决。"
        "你可能会被当作邪恶阵营或爪牙角色。",
      ),
      ("祭品", "如果一名邪恶玩家死于处决，从现在开始，你随时有可能死亡。"),
    ],
    "minion": [
      ("八不郎", "每个夜晚，你要选择一名存活玩家，明天白天他不可以发出声音，否则他可能会被处决。"),
      (
        "婴氏狐女",
        "在你的首个夜晚，你要选择一个善良玩家，他醉酒并且你获得他的能力。"
        "如果你死亡，他恢复健康并加入邪恶阵营。",
      ),
      (
        "冥府钦差",
        "每个夜晚，你要选择一名玩家，从现在开始直到黎明时，他发动能力选择玩家时视为选择了他自己。",
      ),
      (
        "紫僵",
        "首夜，X名善良角色的技能必定获得错误信息，你死亡。每个白天，你可以提名并将投票标记调整为一。"
        "（X为游戏初始设置时镇民数量的一半，向上取整）",
      ),
    ],
    "demon": [
      (
        "奈何",
        "每个夜晚*，你要选择一名玩家，他死亡。首夜，你得知谁是失忆者，每局游戏限一次，"
        "你可以知晓当天失忆者提出的问题，并代替说书人给出答案。[+2失忆者]",
      ),
      (
        "刑天",
        "每个夜晚*，你要选择一名玩家，他死亡。如果你被处决，你的能力改为：“每个夜晚*，"
        "可能会有一名玩家死亡。当你首次死亡后，你存活，但会被视作死亡。”",
      ),
      (
        "百鬼夜行",
        "每个夜晚*，你要选择一名玩家，他死亡。在你的首个夜晚，你查看残缺的魔典并选择初始爪牙数的"
        "善良玩家，他们将知晓自己加入邪恶方阵营并得知你是恶魔，除你以外的邪恶玩家会被当作善良阵营。"
        "[无爪牙在场]",
      ),
      (
        "黑无常",
        "每个夜晚*，你要选择一名玩家（与之前不同）。从现在开始，他被告知不能提名或投票，即使你已死亡。"
        "在你的第五个白天结束时，邪恶阵营获胜。[+白无常，无爪牙在场，-或+任意数量的外来者]",
      ),
      (
        "白无常",
        "每个夜晚*，你要选择一名玩家（与之前不同）。从现在开始，他被告知不能发动自身能力，即使你已死亡。"
        "在你的第五个白天结束时，邪恶阵营获胜。[+黑无常，无爪牙在场，-或+任意数量的外来者]",
      ),
    ],
    "fabled": [
      ("招魂幡", "当一名邪恶玩家即将死亡时，他可能不会死亡并变成一个不在场的善良角色。"),
      ("六耳猕猴", "每个白天，恶魔可以私下拜访说书人得知一条正确信息。"),
      ("谛听", "说谎最多的玩家身上可能会发生一些不好的事情。"),
      ("食梦貘", "每个夜晚，可能会有一名玩家醉酒。下个白天，他的投票视作1.5票。"),
    ],
  }
  first_order = {
    "百鬼夜行": 1,
    "紫僵": 2,
    "失忆者": 8,
    "奈何": 9,
    "婴氏狐女": 10,
    "八不郎": 11,
    "出马仙": 12,
    "念空和尚": 13,
    "风水学徒": 14,
    "冥府钦差": 15,
    "“鲁班”": 16,
    "奇门遁甲": 17,
    "断命师": 18,
    "符士": 19,
    "江湖骗子": 20,
    "招魂幡": 21,
  }
  other_order = {
    "冥婚媒": 1,
    "赶尸匠": 2,
    "失忆者": 3,
    "奈何": 4,
    "百鬼夜行": 5,
    "刑天": 6,
    "八不郎": 7,
    "冥府钦差": 8,
    "阴童子": 9,
    "黑无常": 10,
    "白无常": 11,
    "“鲁班”": 12,
    "奇门遁甲": 13,
    "断命师": 14,
    "符士": 15,
    "江湖骗子": 16,
    "天师": 17,
    "扶乩": 18,
  }
  setup_roles = {"奈何", "百鬼夜行", "黑无常", "白无常"}
  icon_root = "/audit_icons/惟慕玄兮"
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "惟慕玄兮",
    "author": "天海",
    "notes": [
      note(
        "惟尽人事·不知天命\n本局游戏全程采用闭眼仅统计票数而不公布投票人数的方式。\n"
        "从第二天开始，游戏每有一天平安夜，处决的票数要求便会减1。\n"
        "除此之外，每局游戏都会加入一个传奇角色，但并不会公布具体的传奇角色。",
        '<span style="font-size: 1.08em; font-weight: 900;">惟尽人事·不知天命</span><br>'
        "本局游戏全程采用闭眼仅统计票数而不公布投票人数的方式。<br>"
        "从第二天开始，游戏每有一天平安夜，处决的票数要求便会减1。<br>"
        "除此之外，每局游戏都会加入一个传奇角色，但并不会公布具体的传奇角色。",
      ),
      note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚"),
    ],
  }]
  for team, team_roles in roles.items():
    for name, ability in team_roles:
      first_night = first_order.get(name, 0)
      other_night = other_order.get(name, 0)
      image_name = name.strip("“”")
      entries.append(custom_character(
        name,
        team,
        ability=ability,
        image=f"{icon_root}/{image_name}.png",
        firstNight=first_night,
        firstNightReminder=ability if first_night else "",
        otherNight=other_night,
        otherNightReminder=ability if other_night else "",
        setup=int(name in setup_roles),
      ))
  return entries


def curse_of_the_spire() -> list[dict[str, Any]]:
  roles = {
    "townsfolk": [
      ("铁甲战士", "你不会被诅咒。如果你堕落，当晚你得知所有玩家所在的楼层。"),
      ("静默猎手", "如果你没有堕落，每个夜晚*，你会得知当晚你处于的楼层是否存在邪恶玩家。"),
      (
        "故障机器人",
        "每局游戏限一次，如果你没有堕落且上个白天没有行动，在夜晚时*，"
        "你可以得知哪些邪恶角色在场以及他们当晚所在的位置。",
      ),
      (
        "观者",
        "在你的首个夜晚，你要选择一个形态：1.平静：你不会中毒、醉酒、获得错误信息。"
        "2.愤怒：你可以额外“行动”一次。",
      ),
      (
        "亡命之人",
        "每局游戏限一次，你可以公开选择一名玩家，如果他是爪牙或者他被诅咒，他立刻被处决。"
        "[+0～1诅咒]",
      ),
      (
        "亡灵契约师",
        "每局游戏限一次，在夜晚时，你可以选择一名玩家，当他首次将要堕落时，他不会堕落，"
        "然后你得知此事。",
      ),
      (
        "储君",
        "每个夜晚，如果你没有行动且未堕落，你获得两点辉星然后你可以消耗X点辉星，"
        "然后获得一个在角色能力表中顺位为X的镇民的能力。",
      ),
    ],
    "outsider": [
      ("凡庸", "你始终位于你的初始位置，但你会以为自己进行了移动且可以正常的进行“行动”。"),
      ("疑虑", "你不会得知你堕落，你堕落后会中毒且通过行动获取的信息的正误由说书人决定。"),
      ("傲慢", "你获得的所有信息正误反转。"),
    ],
    "minion": [
      (
        "尖塔之盾",
        "在你的首个夜晚，你要选择一个楼层，该层善良玩家获得的所有信息正误反转。"
        "每个夜晚，你会得知所有玩家的位置。",
      ),
      (
        "尖塔之矛",
        "在你的首个夜晚，你得知诅咒的数量，然后查看魔典并决定哪些诅咒在哪些镇民身上。"
        "[+1诅咒]",
      ),
    ],
    "demon": [
      (
        "腐化之心",
        "每个夜晚*，你选择一个楼层，当晚位于该层的存活善良玩家会堕落且得知此事，"
        "如果所有存活善良玩家均堕落或第四个白天结束时，邪恶阵营获胜。",
      ),
    ],
    "fabled": [
      (
        "行动",
        "每名未堕落的存活玩家每局限一次，在白天时，你可以拜访说书人并选择一项。"
        "1）得知本层有哪些玩家。2）选择一名玩家并得知他的阵营，如果他与你处于不同层，你得知错误信息。"
        "3）选择一个角色得知他是否在场，你和该角色之间有人被诅咒，你获得错误信息。",
      ),
      (
        "尖塔",
        "游戏开始时，所有玩家要秘密选择尖塔的上/中/下层作为初始位置。"
        "每个夜晚*，存活玩家可以进行一次移动。",
      ),
      (
        "尖塔商人",
        "你没有阵营且不会进入尖塔以及参与行动。每局游戏限一次，你可以跟说书人共同制定一个道具并公开其效果。"
        "每个玩家可以私下告诉你他的购买代价，当晚你可以选择其中一名玩家获得道具。",
      ),
    ],
  }
  first_order = {
    "储君": 1,
    "尖塔之矛": 8,
    "尖塔": 9,
    "尖塔之盾": 10,
    "观者": 11,
    "亡灵契约师": 12,
  }
  other_order = {
    "尖塔商人": 1,
    "尖塔": 2,
    "储君": 3,
    "亡灵契约师": 4,
    "腐化之心": 5,
    "尖塔之盾": 6,
    "铁甲战士": 7,
    "静默猎手": 8,
    "故障机器人": 9,
  }
  setup_roles = {"亡命之人", "尖塔之矛", "尖塔"}
  icon_root = "/audit_icons/尖塔的诅咒"
  entries: list[dict[str, Any]] = [{
    "id": "_meta",
    "name": "尖塔的诅咒",
    "author": "小烯C2H43g",
    "description": (
      "涅奥是司管复活的先古之民，他被放逐到了高塔的底端。寻求复仇的涅奥会给予外来人祝福，"
      "利用他们来达成自己的目的。那些被涅奥复活的人们只能零碎想起自己过去人生的记忆，"
      "他们被诅咒要永远战斗下去。"
    ),
    "notes": [
      note(
        "诅咒\n游戏初始设置中的外来者将被替换为被诅咒的镇民，每名镇民玩家最多受到一个诅咒。\n"
        "邪恶玩家会互认且得知不在场身份。",
        '<span style="font-size: 1.08em; font-weight: 900;">诅咒</span><br>'
        "游戏初始设置中的外来者将被替换为被诅咒的镇民，每名镇民玩家最多受到一个诅咒。<br>"
        "邪恶玩家会互认且得知不在场身份。",
      ),
      note("*代表非首个夜晚", "<strong>*代表</strong>非首个夜晚"),
    ],
  }]
  for team, team_roles in roles.items():
    for name, ability in team_roles:
      first_night = first_order.get(name, 0)
      other_night = other_order.get(name, 0)
      entries.append(custom_character(
        name,
        team,
        ability=ability,
        image=f"{icon_root}/{name}.png",
        firstNight=first_night,
        firstNightReminder=ability if first_night else "",
        otherNight=other_night,
        otherNightReminder=ability if other_night else "",
        setup=int(name in setup_roles),
      ))
  return entries


def main() -> None:
  scripts = {
    ROOT / "all_jsons" / "特别的玩法" / "#试胆大会-Lei的剧本钟楼.json": trial_by_ghost(),
    ROOT / "all_jsons" / "汀西维尔剧本" / "#饕餮盛宴·汀-清清.json": taotie_feast(),
    ROOT / "all_jsons" / "汀西维尔剧本" / "#大限将至·汀-清清Jungle.json": deadline_approaches(),
    ROOT / "all_jsons" / "全原创角色剧本" / "国内" / "#欧利蒂丝庄园-自逍遥.json": orletis_manor(),
    ROOT / "all_jsons" / "华灯初上剧本创作大赛" / "#效死之徒Ⅱ-摸鱼学徒.json": devotees_two(),
    ROOT / "all_jsons" / "SUI染钟楼投稿&火乐杯剧本" / "#回到三月之前-星火乐.json": return_before_march(),
    ROOT / "all_jsons" / "全原创角色剧本" / "国内" / "西風謎團.json": favonius_mystery_v15(),
    ROOT / "all_jsons" / "来源核对补全" / "#惟慕玄兮-1163722454067052600.json": wei_mu_xuan_xi(),
    ROOT / "all_jsons" / "来源核对补全" / "#尖塔的诅咒-1165934130277384232.json": curse_of_the_spire(),
  }
  for path, items in scripts.items():
    write_script(path, items)


if __name__ == "__main__":
  main()
