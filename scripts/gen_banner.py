#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号文章顶部 Banner 图生成（主题色）。

900x320，主题色背景 + 半透明装饰圆 + 居中白色标题与副标题。
微信对 div 背景色过滤严重，首图必须用图片，因此把 Banner 渲染成图片。
用法：
  python gen_banner.py --title "主标题" --subtitle "副标题" --out banner.png [--theme blue]
依赖 Pillow：pip install Pillow
"""
import os
import sys
import json
import argparse
from PIL import Image, ImageDraw, ImageFont

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_FILE = os.path.join(SKILL_DIR, "themes.json")

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


def load_theme_banner_bg(theme_key, fallback="#1E5BFF"):
    try:
        themes = json.load(open(THEME_FILE, encoding="utf-8"))
    except Exception:
        return fallback
    t = themes.get(theme_key)
    return t.get("banner_bg", t.get("cover_bg", fallback)) if t else fallback


def wrap_text(text, font, draw, max_width):
    """按字符折行，返回 (lines, block_height, line_height)，保证每行不超过 max_width。"""
    text = text.strip()
    if not text:
        return [], 0, 0
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        # 优先尝试不断词；单字符超宽时强制换行
        if current and draw.textlength(test, font=font) > max_width:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    line_height = int(font.size * 1.35)
    block_height = len(lines) * line_height
    return lines, block_height, line_height


def gen_banner(title, subtitle, out, bg_hex, w=900, h=320):
    bg = hex_to_rgb(bg_hex)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # 半透明白色装饰圆（用 alpha 合成，营造层次）
    overlay = Image.new("RGB", (w, h), (255, 255, 255))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([w - 220, -100, w + 140, 260], fill=28)
    md.ellipse([-90, h - 170, 210, h + 90], fill=18)
    img = Image.composite(overlay, img, mask)
    draw = ImageDraw.Draw(img)

    margin_top = 55
    margin_bottom = 55
    gap = 22
    max_width = w * 0.88

    # 主标题：从大字开始试，自动折行 + 字号缩减，直到整块高度放进 Banner
    for main_size in range(78, 27, -4):
        main_font = load_font(main_size)
        title_lines, title_h, title_line_h = wrap_text(title, main_font, draw, max_width)

        # 副标题：用固定小字号，也自动折行
        if subtitle:
            sub_size = min(26, int(main_size * 0.42))
            sub_font = load_font(sub_size)
            sub_lines, sub_h, sub_line_h = wrap_text(subtitle, sub_font, draw, max_width)
            # 副标题最多显示 3 行，超出则省略
            if len(sub_lines) > 3:
                last = sub_lines[2]
                # 尝试加省略号，若仍超宽则去掉最后一个字符
                ellipsis = "…"
                test = last + ellipsis
                while draw.textlength(test, font=sub_font) > max_width and len(test) > 1:
                    test = test[:-2] + ellipsis
                sub_lines = sub_lines[:2] + [test]
                sub_h = 3 * sub_line_h
        else:
            sub_lines, sub_h, sub_font, sub_line_h = [], 0, None, 0

        total_h = title_h + (gap + sub_h if sub_h else 0)
        if total_h <= h - margin_top - margin_bottom:
            break
    else:
        # 极限情况也按最小字号渲染
        main_size = 28
        main_font = load_font(main_size)
        title_lines, title_h, title_line_h = wrap_text(title, main_font, draw, max_width)
        sub_size = 24
        sub_font = load_font(sub_size)
        sub_lines, sub_h, sub_line_h = wrap_text(subtitle, sub_font, draw, max_width)
        if len(sub_lines) > 3:
            sub_lines = sub_lines[:3]
            sub_h = 3 * sub_line_h

    # 整体垂直居中
    total_h = title_h + (gap + sub_h if sub_h else 0)
    start_y = (h - total_h) / 2

    # 绘制主标题（每行居中）
    y = start_y
    for line in title_lines:
        tw = draw.textlength(line, font=main_font)
        draw.text(((w - tw) / 2, y), line, font=main_font, fill=(255, 255, 255))
        y += title_line_h

    # 绘制副标题
    if sub_lines:
        y += gap
        for line in sub_lines:
            tw = draw.textlength(line, font=sub_font)
            draw.text(((w - tw) / 2, y), line, font=sub_font, fill=(255, 255, 255))
            y += sub_line_h

    img.save(out)
    print(f"✅ Banner 已生成：{out}（底色 {bg_hex}，标题字号 {main_size}，折 {len(title_lines)} 行）")


def main():
    p = argparse.ArgumentParser(description="生成公众号主题色 Banner 图")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--theme", default="")
    p.add_argument("--bg", default="", help="直接指定底色 #RRGGBB，优先级高于 --theme")
    p.add_argument("--w", type=int, default=900)
    p.add_argument("--h", type=int, default=320)
    args = p.parse_args()

    if args.bg:
        bg_hex = args.bg
    elif args.theme:
        bg_hex = load_theme_banner_bg(args.theme)
        print(f"🎨 采用主题「{args.theme}」Banner 底色 {bg_hex}")
    else:
        bg_hex = "#1E5BFF"

    gen_banner(args.title, args.subtitle, args.out, bg_hex, args.w, args.h)


if __name__ == "__main__":
    main()
