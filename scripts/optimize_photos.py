#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
optimize_photos.py — 生成网页用压缩版照片
data/img/N.jpg（原图，部分为几十MB的PNG内容）→ data/img_web/N.jpg
最长边 1800px、JPEG q80（约190DPI @215mm，背景层足够）
"""
import os, sys, time
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "img")
OUT  = os.path.join(os.path.dirname(__file__), "..", "data", "img_web")
MAX, Q = 1800, 80

def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted((f for f in os.listdir(ROOT) if f.split(".")[0].isdigit()),
                   key=lambda s: int(s.split(".")[0]))
    t0, done, skip = time.time(), 0, 0
    for f in files:
        src, dst = os.path.join(ROOT, f), os.path.join(OUT, f)
        if os.path.exists(dst):
            skip += 1; continue
        try:
            im = Image.open(src)
            if im.format == "JPEG":
                im.draft("RGB", (MAX, MAX))          # 快速解码
            im = im.convert("RGB")
            im.thumbnail((MAX, MAX), Image.LANCZOS)
            im.save(dst, "JPEG", quality=Q, optimize=True)
            done += 1
            if done % 50 == 0:
                print(f"  … {done} 张，耗时 {time.time()-t0:.0f}s")
        except Exception as e:
            print(f"[失败] {f}: {e}")
    print(f"完成: 新压缩 {done} 张，已存在跳过 {skip} 张，输出目录 data/img_web/")

if __name__ == "__main__":
    main()
