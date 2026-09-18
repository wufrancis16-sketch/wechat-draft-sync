#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号大字报风格封面生成。

随机底色（鲜艳/深色系，保证白字可读），居中超大标题文字，白字加黑描边突出。
用法：
  python gen_cover.py --title "标题文字" --out cover.png
      [--bg #RRGGBB]           固定底色
      [--theme <key>]          从 themes.json 读取该主题的封面底色
      [--w 900 --h 383]
不指定 --bg / --theme 时从预设调色板随机选底色。
依赖 Pillow：pip install Pillow
"""
import os
import sys
import json
import random
import argparse
from PIL import Image, ImageDraw, ImageFont

# 技能根目录（scripts/ 的上一级）
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_FILE = os.path.join(SKILL_DIR, "themes.json")

# 预设底色（深色/鲜艳系，白字可读），仅在没有 --bg/--theme 时随机使用
PALETTE = [
    (30, 91, 255), (214, 40, 40), (18, 138, 103), (123, 31, 162),
    (245, 124, 0), (13, 71, 161), (191, 54, 12), (0, 105, 92),
    (109, 76, 0), (74, 20, 140),
]

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_theme_cover_bg(theme_key):
    """从 themes.json 读取主题的封面底色 cover_bg；找不到返回 None。"""
    try:
        themes = json.load(open(THEME_FILE, encoding="utf-8"))
    except Exception:
        return None
    t = themes.get(theme_key)
    return t.get("cover_bg") if t else None


def wrap_text(text, font, max_width, max_chars=10):
    """按宽度与最大字数折行（中文逐字）"""
    lines = []
    cur = ""
    for ch in text:
        if len(cur) >= max_chars or font.getlength(cur + ch) > max_width:
            if cur:
                lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def gen_cover(title, out, bg_rgb, w, h):
    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 自适应字号：从大往小收，直到总高与行宽都合适
    # 规则：10 个字以内尽量单行显示；超过 10 个字按 max_chars=10 换行；始终居中
    font_size = min(h - 30, 220)
    while font_size > 24:
        font = load_font(font_size)
        if len(title) <= 10:
            # 短标题强制单行，靠缩小字号来适配宽度
            lines = [title]
        else:
            lines = wrap_text(title, font, int(w * 0.92), 10)
        line_h = font_size * 1.12
        total_h = line_h * len(lines)
        max_lw = max(font.getlength(ln) for ln in lines)
        if total_h <= h * 0.86 and max_lw <= w * 0.94:
            break
        font_size -= 4

    line_h = font_size * 1.12
    total_h = line_h * len(lines)
    y = (h - total_h) / 2
    # 黑描边八方向，突出白字
    offsets = [(-2, 0), (2, 0), (0, -2), (0, 2),
               (-2, -2), (2, 2), (-2, 2), (2, -2)]
    for ln in lines:
        lw = font.getlength(ln)
        x = (w - lw) / 2
        for dx, dy in offsets:
            draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255))
        y += line_h

    img.save(out)
    print(f"✅ 封面已生成：{out}（底色 RGB{bg_rgb}，字号 {font_size}）")


def main():
    p = argparse.ArgumentParser(description="生成公众号大字报风格封面")
    p.add_argument("--title", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bg", default="", help="底色 #RRGGBB")
    p.add_argument("--theme", default="", help="主题 key（从 themes.json 读封面底色）")
    p.add_argument("--w", type=int, default=900)
    p.add_argument("--h", type=int, default=383)
    args = p.parse_args()

    bg_rgb = None
    if args.theme:
        bg_hex = load_theme_cover_bg(args.theme)
        if bg_hex:
            bg_rgb = hex_to_rgb(bg_hex)
            print(f"🎨 采用主题「{args.theme}」封面底色 {bg_hex}")
        else:
            print(f"⚠️ 未找到主题「{args.theme}」，回退随机底色")
    if bg_rgb is None and args.bg:
        bg_rgb = hex_to_rgb(args.bg)
    if bg_rgb is None:
        bg_rgb = random.choice(PALETTE)

    gen_cover(args.title, args.out, bg_rgb, args.w, args.h)


if __name__ == "__main__":
    main()
