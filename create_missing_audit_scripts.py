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


def main() -> None:
  scripts = {
    ROOT / "all_jsons" / "特别的玩法" / "#试胆大会-Lei的剧本钟楼.json": trial_by_ghost(),
    ROOT / "all_jsons" / "汀西维尔剧本" / "#饕餮盛宴·汀-清清.json": taotie_feast(),
    ROOT / "all_jsons" / "汀西维尔剧本" / "#大限将至·汀-清清Jungle.json": deadline_approaches(),
    ROOT / "all_jsons" / "全原创角色剧本" / "国内" / "#欧利蒂丝庄园-自逍遥.json": orletis_manor(),
  }
  for path, items in scripts.items():
    write_script(path, items)


if __name__ == "__main__":
  main()
