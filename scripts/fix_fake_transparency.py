#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fake_transparency.py — 素材「假透明」检测与修复

问题：部分素材下载时把网站预览的棋盘格底纹（白/浅灰交替）截进了像素，
     虽带 alpha 通道但完全不透明，贴到版面上会露出格子。

流程：
  1. 扫描 data/assets/ 全部素材，按边缘颜色分类：
     - real      真透明（alpha 有效）→ 不动
     - fake      假透明（棋盘格/纯浅色底，alpha 全不透明）→ 修复
     - opaque    不透明且背景非浅色 → 只登记不动（可能是设计底色）
  2. 修复方式：从图像边缘 BFS 泛洪，只清除「与背景色一致且与边缘连通」
     的像素 → alpha=0，并对残留抗锯齿边做羽化；内容存为 PNG（文件名不变）。
  3. 原件备份到 data/excluded/fake_alpha_backup/。

用法：python3 scripts/fix_fake_transparency.py [--dry]
"""
import os, sys, shutil
from collections import Counter, deque
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "assets")
BACKUP = os.path.join(os.path.dirname(__file__), "..", "data", "excluded", "fake_alpha_backup")
DRY = "--dry" in sys.argv

def border_stats(im, frac=0.06):
    """统计边缘一圈的颜色（量化到 /16 桶），返回 (top2桶, 覆盖率, top2精确色)"""
    rgb = im.convert("RGB"); w, h = rgb.size
    bw = max(2, int(w * frac)); bh = max(2, int(h * frac))
    buckets, exact = Counter(), Counter()
    pts = ([(x, y) for x in range(0, w, 2) for y in list(range(0, bh, 2)) + list(range(h - bh, h, 2))] +
           [(x, y) for y in range(0, h, 2) for x in list(range(0, bw, 2)) + list(range(w - bw, w, 2))])
    for x, y in pts:
        p = rgb.getpixel((x, y))
        buckets[(p[0]//16, p[1]//16, p[2]//16)] += 1
        exact[p] += 1
    total = sum(buckets.values()) or 1
    top2 = buckets.most_common(2)
    cov = sum(c for _, c in top2) / total
    # 主桶对应的精确代表色
    reps = []
    for b, _ in top2:
        reps.append(max((c for c in exact if (c[0]//16, c[1]//16, c[2]//16) == b),
                        key=lambda c: exact[c]))
    return top2, cov, reps

def is_neutral_light(c):
    r, g, b = c
    return max(abs(r-g), abs(g-b), abs(r-b)) <= 18 and (r + g + b) / 3 >= 165

def classify(path):
    im = Image.open(path)
    rgba = im.convert("RGBA")
    a = rgba.split()[3]
    hist = a.histogram()
    if sum(hist[:16]) > rgba.size[0] * rgba.size[1] * 0.02:   # >2% 像素真透明
        return "real", None
    top2, cov, reps = border_stats(rgba)
    if cov >= 0.70 and all(is_neutral_light(c) for c in reps[:2] if reps):
        kind = "fake" if len([c for c in top2 if c[1] > 0]) >= 1 else "fake"
        return "fake", reps
    return "opaque", reps

def remove_bg(path, reps):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    cols = [c for c in reps if c]

    def near(p, tol):
        return any(abs(p[0]-c[0]) <= tol and abs(p[1]-c[1]) <= tol and abs(p[2]-c[2]) <= tol for c in cols)

    seen = [[False]*w for _ in range(h)]
    dq = deque()
    for x in range(w):
        for y in (0, h-1):
            if not seen[y][x] and near(px[x, y], 14):
                seen[y][x] = True; dq.append((x, y))
    for y in range(h):
        for x in (0, w-1):
            if not seen[y][x] and near(px[x, y], 14):
                seen[y][x] = True; dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and near(px[nx, ny], 14):
                seen[ny][nx] = True; dq.append((nx, ny))

    removed = 0
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                r, g, b, _ = px[x, y]; px[x, y] = (r, g, b, 0); removed += 1
    # 羽化：紧邻透明区、颜色接近背景的残留像素（抗锯齿边）降为半透明
    for y in range(1, h-1):
        for x in range(1, w-1):
            if not seen[y][x] and (seen[y][x+1] or seen[y][x-1] or seen[y+1][x] or seen[y-1][x]):
                if near(px[x, y], 30):
                    r, g, b, _ = px[x, y]; px[x, y] = (r, g, b, 90)
    return removed / (w * h), im

def main():
    files = sorted((f for f in os.listdir(ROOT) if f.split(".")[0].isdigit()),
                   key=lambda s: int(s.split(".")[0]))
    groups = {"real": [], "fake": [], "opaque": []}
    reps_map = {}
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        try:
            kind, reps = classify(p)
            groups[kind].append(f); reps_map[f] = reps
        except Exception as e:
            print(f"[错误] {f}: {e}")

    print(f"真透明(不动): {len(groups['real'])} 个")
    print(f"假透明(修复): {len(groups['fake'])} 个 → {groups['fake'][:20]}{' …' if len(groups['fake'])>20 else ''}")
    print(f"不透明/设计底色(登记不动): {len(groups['opaque'])} 个 → {groups['opaque'][:20]}{' …' if len(groups['opaque'])>20 else ''}")

    if DRY:
        print("dry 模式，未修改文件"); return
    os.makedirs(BACKUP, exist_ok=True)
    ok = 0
    for f in groups["fake"]:
        p = os.path.join(ROOT, f)
        try:
            shutil.copy2(p, os.path.join(BACKUP, f))       # 备份原件
            ratio, im = remove_bg(p, reps_map[f])
            im.save(p, "PNG")                              # 内容为 PNG，文件名保持 N.jpg（浏览器按内容识别）
            ok += 1
        except Exception as e:
            print(f"[修复失败] {f}: {e}")
    print(f"已修复 {ok}/{len(groups['fake'])} 个（原件备份在 data/excluded/fake_alpha_backup/）")

if __name__ == "__main__":
    main()
