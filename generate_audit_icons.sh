#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SOURCE="$ROOT/bilibili_script_audit/剧本/欧利蒂丝庄园-1045287330677522438/对照图-02.png"
OUTPUT="$ROOT/script_editor/public/audit_icons/欧利蒂丝庄园"
mkdir -p "$OUTPUT"

crop_icon() {
  name=$1
  x=$2
  y=$3
  magick "$SOURCE" -crop "80x80+$x+$y" +repage -resize 180x180 "$OUTPUT/$name.png"
}

crop_icon 冒险家 110 250
crop_icon 小女孩 110 350
crop_icon 先知 110 440
crop_icon 医生 110 530
crop_icon 律师 110 625
crop_icon 哭泣小丑 110 725
crop_icon 机械师 110 825
crop_icon 病患 730 250
crop_icon 心理学家 730 350
crop_icon 拉拉队员 730 455
crop_icon 逃脱大师 730 555
crop_icon 古董商 730 665
crop_icon 佣兵 720 725
crop_icon 调酒师 110 1000
crop_icon 盲女 110 1085
crop_icon 幸运儿 730 985
crop_icon 木偶师 730 1085
crop_icon 摄影师 110 1220
crop_icon 梦之女巫 110 1350
crop_icon 宿伞白魂 730 1220
crop_icon 噩梦 730 1340
crop_icon 红蝶 110 1490
crop_icon 厂长 110 1590
crop_icon 使徒 730 1490
crop_icon 宿伞黑魂 730 1590
