#!/bin/bash
# ============================================================
# shuffle_rename.sh — 随机打乱顺序后，把目录内所有文件重命名为 1.jpg ~ N.jpg
#
# 用法: ./scripts/shuffle_rename.sh <目录> [扩展名]
#   例: ./scripts/shuffle_rename.sh data/img jpg
#       ./scripts/shuffle_rename.sh data/assets jpg
#
# 特点:
#   1. 先随机洗牌再编号，编号与原目录顺序无关
#   2. 两阶段改名（先改临时名），避免 5.jpg → 3.jpg 这类同名覆盖
#   3. 生成映射表 data/<目录名>_rename_map.csv，可追溯原名
#   4. 跳过 .DS_Store 和临时文件，可重复执行（幂等）
# ============================================================
set -euo pipefail

DIR="${1:?用法: $0 <目录> [扩展名]}"
EXT="${2:-jpg}"

cd "$DIR"

# 幂等检查：如果全部已是 数字.ext 形式则提示后退出
if [ -z "$(ls -1 | grep -v -E "^[0-9]+\.${EXT}$")" ]; then
  echo "跳过：$DIR 内文件已全部为 数字.$EXT 命名"
  exit 0
fi

LIST=$(mktemp)
trap 'rm -f "$LIST"' EXIT
MAP="../$(basename "$DIR")_rename_map.csv"

# 1) 收集所有普通文件（排除系统/临时文件），用 python3 随机打乱（shuf 在 macOS 不可用）
find . -maxdepth 1 -type f ! -name '.DS_Store' ! -name '.__tmp__*' -print0 \
  | python3 -c "
import random, sys
names = sys.stdin.buffer.read().split(b'\0')
names = [n for n in names if n]
random.shuffle(names)
sys.stdout.buffer.write(b'\0'.join(names) + b'\0')
" > "$LIST"

# 2) 阶段一：按随机顺序改成临时名，同时记录映射
total=0
echo "old_name,new_name" > "$MAP"
while IFS= read -r -d '' f; do
  total=$((total+1))
  mv "$f" ".__tmp__$total"
  printf '"%s","%d.%s"\n' "${f#./}" "$total" "$EXT" >> "$MAP"
done < "$LIST"

# 3) 阶段二：临时名 → 最终编号名
for f in .__tmp__*; do
  n="${f#.__tmp__}"
  mv "$f" "$n.$EXT"
done

echo "完成: $DIR 共 $total 个文件 → 1.${EXT} ~ $total.${EXT}（映射表: data/$(basename "$DIR")_rename_map.csv）"
