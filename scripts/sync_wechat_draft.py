#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信公众号草稿箱同步脚本（支持主题配色自动生成）。

Workflow:
  1. appid + appsecret -> access_token
  2. 若提供 --theme：
     - 自动按主题色生成封面（封面标题用 --cover-title，默认可缺省用 --title）
     - 若 HTML 含 {{BANNER_URL}} 占位符，自动按主题色生成 Banner 并上传替换
     - 将 HTML 中的 {{THEME_COLOR}} {{TINT_COLOR}} {{END_COLOR}} {{END_BG}}
       {{QR_URL}} {{WECHAT_ID}} 占位符替换为对应主题色与 config 中的二维码/微信号
  3. 上传封面图为永久素材 -> thumb_media_id
  4. 调用 draft/add 创建草稿

凭证仅通过命令行参数或环境变量传入，不写入任何文件。
正文默认提取 "## 正文内容" 到 "**核心观点**" 之间的内容；若不匹配则回退为全文。
"""
import os
import re
import sys
import json
import argparse
import tempfile
import subprocess

try:
    import requests
except ImportError:
    sys.exit("缺少依赖 requests：请先 `pip install requests markdown`")

try:
    import markdown
except ImportError:
    sys.exit("缺少依赖 markdown：请先 `pip install requests markdown`")

try:
    import ima_media
except ImportError as e:
    ima_media = None
    print(f"[warn] 无法加载 ima_media 模块，自动插图功能不可用：{e}", file=sys.stderr)


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_FILE = os.path.join(SKILL_DIR, "themes.json")
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")
GEN_COVER = os.path.join(SKILL_DIR, "scripts", "gen_cover.py")
GEN_BANNER = os.path.join(SKILL_DIR, "scripts", "gen_banner.py")


def get_token(appid, appsecret):
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": appid, "secret": appsecret}
    r = requests.get(url, params=params, timeout=10).json()
    if "access_token" not in r:
        raise SystemExit(f"❌ 获取 access_token 失败：{r}")
    return r["access_token"]


def upload_image(token, image_path):
    """上传图片永久素材，返回包含 media_id 和 url 的字典。"""
    if not os.path.exists(image_path):
        raise SystemExit(f"❌ 图片文件不存在：{image_path}")
    size = os.path.getsize(image_path)
    if size > 2 * 1024 * 1024:
        print(f"⚠️ 图片 {size/1024/1024:.1f}MB 超过 2MB，上传可能失败，建议压缩")
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    with open(image_path, "rb") as f:
        r = requests.post(url, files={"media": f}, timeout=30).json()
    if "media_id" not in r:
        raise SystemExit(f"❌ 上传图片失败：{r}")
    return r


def fetch_and_upload_product_images(topic, token, config, work_dir):
    """根据主题识别产品，从 ima 抓取产品图并上传到微信，返回 (slot->url, product_name)。"""
    if not topic or not ima_media:
        return {}, ""
    product_map = config.get("product_image_map", {})
    if not product_map:
        return {}, ""
    product = ima_media.detect_product(topic, product_map)
    if not product:
        print(f"[auto-img] 主题「{topic}」未匹配到任何产品素材映射")
        return {}, ""
    cfg = product_map[product]
    print(f"[auto-img] 主题命中产品「{product}」，开始从 ima 抓取产品图...")
    out_dir = os.path.join(work_dir, "product_imgs")
    fetched = ima_media.fetch_product_images(cfg, config["ima"]["ima_api_script"], out_dir)
    slot_urls = {}
    for slot, path in fetched.items():
        if not path:
            continue
        try:
            info = upload_image(token, path)
            url = info.get("url", "")
            if not url:
                print(f"[auto-img] {slot} 上传成功但未返回 url，跳过嵌入")
                continue
            slot_urls[slot] = url
            print(f"[auto-img] {slot} 已上传微信（{os.path.getsize(path)/1024:.0f}KB）")
        except Exception as e:
            print(f"[auto-img] {slot} 上传失败：{e}", file=sys.stderr)
    return slot_urls, product


def _img_block(url, product_name, slot):
    """统一的插图块样式。"""
    return (
        f'<p style="text-align:center;margin:18px 0;">'
        f'<img src="{url}" style="max-width:100%;height:auto;border-radius:8px;" '
        f'alt="{product_name}产品截图-{slot}">'
        f'</p>'
    )


def _safe_anchors(html):
    """收集「可安全插入 <p> 块」的偏移：正文段落 </p> 之后。

    只取有实际文字（≥40 字）且不含图片的段落，避免把图插到标题与正文之间、
    或插到图片段落旁边。绝不返回裸字符偏移（历史上曾把首行 <div ...> 切坏）。
    """
    anchors = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p\s*>", html, re.S | re.I):
        inner = m.group(1)
        if "<img" in inner.lower():
            continue
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if len(text) >= 40:
            anchors.append(m.end())
    return anchors


def _spread_picks(anchors, n):
    """在 anchors 中均匀挑 n 个位置，避免集中。"""
    if not anchors:
        return []
    if n >= len(anchors):
        return list(anchors)
    if n == 1:
        return [anchors[len(anchors) // 2]]
    step = (len(anchors) - 1) / (n + 1)
    picks, taken = [], set()
    for i in range(1, n + 1):
        idx = int(round(step * i))
        while idx in taken and idx < len(anchors) - 1:
            idx += 1
        taken.add(idx)
        picks.append(anchors[idx])
    return picks


def insert_product_images(html, slot_urls, product_name):
    """把产品图 URL 插入 HTML。

    1) 优先替换 {{IMG_<SLOT>}} 占位符（位置精准，作者可控）；
    2) 多出来的图均匀分散到正文段落之后（安全锚点，不会切坏标签）；
    3) 若一个安全锚点都没有，则插到最后一个 </div> 之前。
    """
    if not slot_urls:
        return html
    slots = list(slot_urls.items())

    # 1) 占位符替换
    used = set()
    for slot, url in slots:
        placeholder = f"{{{{IMG_{slot.upper()}}}}}"
        if placeholder in html:
            html = html.replace(placeholder, _img_block(url, product_name, slot), 1)
            used.add(slot)

    # 2) 未命中占位符的图 → 分散插入安全锚点
    fallback = [(s, u) for s, u in slots if s not in used]
    if not fallback:
        return html

    blocks = [_img_block(u, product_name, s) for s, u in fallback]
    picks = _spread_picks(_safe_anchors(html), len(blocks))

    if not picks:
        # 兜底：插到最后一个 </div> 之前（没有 </div> 则追加到末尾）
        closes = list(re.finditer(r"</div\s*>", html, re.I))
        pos = closes[-1].start() if closes else len(html)
        picks = [pos] * len(blocks)
    elif len(picks) < len(blocks):
        # 锚点不够，剩余的放到最后一个锚点
        picks = picks + [picks[-1]] * (len(blocks) - len(picks))

    # 从后往前插入，避免位置偏移
    for pos, block in sorted(zip(picks, blocks), key=lambda x: x[0], reverse=True):
        html = html[:pos] + block + html[pos:]
    return html


def extract_body(md_path):
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"##\s*正文内容\s*(.*?)\*\*核心观点\*\*", text, re.S)
    if m:
        return m.group(1).strip()
    # 回退：若没有标记，返回全文
    return text.strip()


def build_html_from_md(md_path):
    """从 markdown 提取正文并套用默认微信排版样式。"""
    body = extract_body(md_path)
    html = markdown.markdown(body, extensions=["extra"])
    html = re.sub(r"<strong>", '<strong style="font-size:17px;line-height:2;">', html)
    html = re.sub(
        r"<h([2-4])>",
        lambda m: f'<h{m.group(1)} style="font-size:17px;line-height:2;font-weight:bold;">',
        html,
    )
    return f'<div style="font-size:16px;line-height:2;">{html}</div>'


def check_html_integrity(html):
    """发布前体检：① 标签未被切坏 ② 无残留占位符。

    历史 bug：fallback 插图插到裸字符偏移 0+5，把首行 <div ...> 切成
    `<div <p>…图…</p>style="font-size:16px;…">`，正文开头出现图片 + 一行代码。
    """
    bad = re.search(r"<[a-zA-Z][^<>]*<", html, re.S)
    if bad:
        snippet = html[max(0, bad.start() - 40): bad.start() + 80]
        raise SystemExit(f"❌ HTML 结构异常（标签被切坏），已阻止同步：{snippet!r}")
    leftovers = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", html)))
    if leftovers:
        print(f"⚠️ 仍有未替换占位符：{leftovers}", file=sys.stderr)


def add_draft(token, thumb_media_id, html, title, author, digest):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": html,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    payload = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    r = requests.post(
        url, data=payload, headers={"Content-Type": "application/json"}, timeout=30
    ).json()
    if "media_id" not in r:
        raise SystemExit(f"❌ 创建草稿失败：{r}")
    return r["media_id"]


# ---------------------- 主题 / 配置 ----------------------

def load_themes():
    if os.path.exists(THEME_FILE):
        try:
            return json.load(open(THEME_FILE, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def load_config():
    """读取 config.json；若不存在则回退到 config.example.json（便于新环境首次跑通）。"""
    for path in (CONFIG_FILE, os.path.join(SKILL_DIR, "config.example.json")):
        if os.path.exists(path):
            try:
                cfg = json.load(open(path, encoding="utf-8"))
                if path.endswith("config.example.json"):
                    print(f"[warn] 未找到 config.json，正使用示例配置 {path}；"
                          f"请复制为 config.json 并填入你自己的二维码/微信号/知识库 ID。",
                          file=sys.stderr)
                return cfg
            except Exception:
                return {}
    return {}


def get_theme(theme_key, config):
    themes = load_themes()
    if not theme_key:
        theme_key = config.get("default_theme", "blue")
    return themes.get(theme_key, themes.get("blue", {})), theme_key


def apply_theme(html, theme, config):
    """替换 HTML 中的主题占位符。"""
    end_color = theme.get("end_color", theme.get("theme", "#1E5BFF"))
    end_bg = theme.get("end_bg", theme.get("tint", "#E8F0FE"))
    repl = {
        "{{THEME_COLOR}}": theme.get("theme", "#1E5BFF"),
        "{{TINT_COLOR}}": theme.get("tint", "#E8F0FE"),
        "{{END_COLOR}}": end_color,
        "{{END_BG}}": end_bg,
        "{{QR_URL}}": config.get("qr_url", ""),
        "{{WECHAT_ID}}": config.get("wechat_id", ""),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


def run_gen(script, *cli_args):
    """调用 gen_cover / gen_banner 脚本生成图片。"""
    cmd = [sys.executable, script, *cli_args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"❌ 生成图片失败：{r.stderr or r.stdout}")
    return r.stdout.strip()


# ---------------------- 主流程 ----------------------

def main():
    p = argparse.ArgumentParser(description="同步文章到公众号草稿箱（支持主题配色）")
    p.add_argument("--appid", default=os.environ.get("WECHAT_APPID", ""))
    p.add_argument("--appsecret", default=os.environ.get("WECHAT_APPSECRET", ""))
    p.add_argument("--md", default="", help="文章 markdown 文件路径（与 --html 二选一）")
    p.add_argument("--html", default="", help="自定义 HTML 文件路径，提供则跳过 markdown 转换")
    p.add_argument("--cover", default="", help="封面图片路径；省略且提供 --theme 时自动生成")
    p.add_argument("--title", required=True, help="草稿标题")
    p.add_argument("--author", default="")
    p.add_argument("--digest", default="")
    p.add_argument("--thumb", default="", help="已有的封面永久素材 media_id，提供则跳过上传")
    p.add_argument("--theme", default="", help="主题 key（见 themes.json），自动搭配封面/Banner/配色")
    p.add_argument("--cover-title", default="", help="封面大字标题，默认同 --title")
    p.add_argument("--banner-title", default="", help="Banner 主标题，默认同 --title")
    p.add_argument("--banner-sub", default="", help="Banner 副标题，默认同 --digest")
    p.add_argument("--topic", default="", help="文章主题，用于自动匹配产品并从 ima 知识库抓取产品图片")
    p.add_argument("--auto-images", action="store_true", help="根据 --topic 自动从 ima 抓取产品图并嵌入文章")
    args = p.parse_args()

    if not args.appid or not args.appsecret:
        raise SystemExit(
            "用法：python sync_wechat_draft.py --appid X --appsecret Y "
            "--html article.html --title \"标题\" [--theme blue] [--cover cover.png]\n"
            "或设置环境变量 WECHAT_APPID / WECHAT_APPSECRET"
        )
    if not args.md and not args.html:
        raise SystemExit("❌ 必须提供 --md 或 --html 其中一个")

    config = load_config()
    theme, theme_key = get_theme(args.theme, config)

    tmp = tempfile.mkdtemp(prefix="wx_")
    token = get_token(args.appid, args.appsecret)
    print("✅ access_token 获取成功")

    # 1) 读取/构建 HTML
    if args.html:
        html = open(args.html, encoding="utf-8").read()
    else:
        html = build_html_from_md(args.md)

    # 2) 主题占位符替换
    if theme:
        html = apply_theme(html, theme, config)
        print(f"🎨 应用主题「{theme_key}」配色")

    # 2.5) 自动从 ima 抓取产品图并上传到微信，嵌入占位符
    if args.auto_images and args.topic:
        slot_urls, product_name = fetch_and_upload_product_images(args.topic, token, config, tmp)
        if slot_urls:
            html = insert_product_images(html, slot_urls, product_name)
            print(f"✅ 已自动嵌入 {len(slot_urls)} 张「{product_name}」产品图")

    # 3) 封面：自动生成 or 使用给定
    if args.thumb:
        thumb = args.thumb
        print(f"⏭️ 使用已有封面 media_id：{thumb}")
    else:
        if not args.cover and theme:
            cover_path = os.path.join(tmp, "cover.png")
            cover_title = args.cover_title or args.title
            run_gen(GEN_COVER, "--title", cover_title, "--out", cover_path, "--theme", theme_key)
            args.cover = cover_path
        if not args.cover:
            raise SystemExit("❌ 未提供 --cover 也未提供 --theme（无法生成封面）")
        cover_info = upload_image(token, args.cover)
        thumb = cover_info["media_id"]
        print(f"✅ 封面素材 media_id：{thumb}")

    # 4) Banner：HTML 含占位符且提供主题时自动生成
    if "{{BANNER_URL}}" in html and theme:
        banner_path = os.path.join(tmp, "banner.png")
        b_title = args.banner_title or args.title
        b_sub = args.banner_sub or args.digest
        run_gen(GEN_BANNER, "--title", b_title, "--subtitle", b_sub,
                "--out", banner_path, "--theme", theme_key)
        banner_info = upload_image(token, banner_path)
        banner_url = banner_info.get("url", "")
        if not banner_url:
            raise SystemExit(f"❌ Banner 上传成功但缺少 url：{banner_info}")
        html = html.replace("{{BANNER_URL}}", banner_url)
        print(f"✅ Banner 素材已上传并嵌入")

    # 5) 同步草稿
    check_html_integrity(html)
    media_id = add_draft(token, thumb, html, args.title, args.author, args.digest)
    print(f"🎉 草稿创建成功，media_id：{media_id}")
    print("请到公众号后台「草稿箱」确认并发布。")


if __name__ == "__main__":
    main()
