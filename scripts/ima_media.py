# -*- coding: utf-8 -*-
"""
ima_media.py — 从 ima 知识库的产品图片素材文件夹里抓取图片。

被 sync_wechat_draft.py 调用：根据文章主题识别产品 -> 列出对应图片素材 -> 按 slot 规则挑选 -> 下载到本地。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple

def _resolve_node() -> str:
    """定位 node 可执行文件：优先 $NODE_BIN，其次 PATH，最后退回裸命令名。"""
    env = os.environ.get("NODE_BIN")
    if env and os.path.exists(env):
        return env
    found = shutil.which("node")
    if found:
        return found
    return "node"


NODE_BIN = _resolve_node()


def _run_ima_api(ima_api_script: str, method: str, body: dict) -> dict:
    """调用 ima_api.cjs，返回 stdout 解析后的 JSON。"""
    client_id = open(os.path.expanduser("~/.config/ima/client_id"), encoding="utf-8").read().strip()
    api_key = open(os.path.expanduser("~/.config/ima/api_key"), encoding="utf-8").read().strip()
    opts = json.dumps({"clientId": client_id, "apiKey": api_key}, ensure_ascii=False)
    cmd = [
        NODE_BIN,
        ima_api_script,
        method,
        json.dumps(body, ensure_ascii=False),
        opts,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"ima_api error: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ima_api stdout is not JSON: {result.stdout[:200]}... ({e})")


def list_folder_images(
    kb_id: str,
    folder_id: str,
    ima_api_script: str,
    recursive: bool = True,
    depth: int = 0,
    max_depth: int = 1,
) -> List[dict]:
    """
    分页列出知识库文件夹下的所有图片素材（media_type=9 或扩展名）。
    默认递归扫描一层子文件夹（recursive=True, max_depth=1），
    以便抓到放在子文件夹（如"智能开单素材"）中的产品图。
    """
    all_items: List[dict] = []
    cursor = ""
    pages = 0
    while pages < 50:
        resp = _run_ima_api(
            ima_api_script,
            "openapi/wiki/v1/get_knowledge_list",
            {
                "knowledge_base_id": kb_id,
                "folder_id": folder_id,
                "cursor": cursor,
                "limit": 50,
            },
        )
        data = resp.get("data", {})
        items = data.get("knowledge_list", []) or data.get("info_list", [])
        if not items:
            break
        all_items.extend(items)
        cursor = data.get("next_cursor", "") or data.get("cursor", "")
        pages += 1
        if data.get("is_end") or not cursor:
            break

    # 仅保留图片：media_type=9 或标题含图片扩展名
    images: List[dict] = []
    subfolders: List[str] = []
    for it in all_items:
        title = it.get("title", "")
        mtype = it.get("media_type")
        if mtype == 9 or re.search(r"\.(png|jpe?g|gif|webp)$", title, re.I):
            images.append({
                "media_id": it["media_id"],
                "title": title,
                "media_type": mtype,
            })
        elif mtype == 99 and recursive and depth < max_depth:
            subfolders.append(it["media_id"])

    # 递归扫描一层子文件夹（拿到子文件夹里的产品图）
    if recursive and depth < max_depth and subfolders:
        for sf in subfolders:
            images.extend(list_folder_images(
                kb_id, sf, ima_api_script,
                recursive=True, depth=depth + 1, max_depth=max_depth,
            ))
    return images


def select_images(all_images: List[dict], slots_config: List[dict]) -> Dict[str, Optional[dict]]:
    """
    按 slot 配置挑选最合适的图片。
    slots_config: [{"slot": "hero", "pick": ["首页"], "alt": "..."}, ...]
    每个 slot 只挑第一张命中的，命中的图片会从候选池移除，避免重复。
    """
    remaining = list(all_images)
    selected: Dict[str, Optional[dict]] = {}
    for rule in slots_config:
        slot = rule["slot"]
        keywords = [kw.lower() for kw in rule.get("pick", [])]
        found = None
        for idx, it in enumerate(remaining):
            title_lower = it.get("title", "").lower()
            if any(kw in title_lower for kw in keywords):
                found = it
                # 复制并加入 alt
                found = dict(found)
                found["alt"] = rule.get("alt", "")
                del remaining[idx]
                break
        selected[slot] = found
    return selected


def get_media_download_url(
    media_id: str,
    ima_api_script: str,
) -> Tuple[str, dict]:
    """
    调用 get_media_info 获取图片的带签名下载 URL 和请求头。
    """
    resp = _run_ima_api(
        ima_api_script,
        "openapi/wiki/v1/get_media_info",
        {"media_id": media_id},
    )
    url_info = resp.get("data", {}).get("url_info", {})
    url = url_info.get("url", "")
    headers = url_info.get("headers", {})
    if not url:
        raise RuntimeError(f"无法获取 media_id={media_id} 的下载 URL")
    return url, headers


def download_image(
    media_id: str,
    out_path: str,
    ima_api_script: str,
) -> None:
    """
    下载单张图片到本地。如果超过微信永久素材 2MB 限制会自动压缩到 1920 宽。
    """
    url, ima_headers = get_media_download_url(media_id, ima_api_script)
    headers = {k: v for k, v in ima_headers.items()}
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    req = urllib.request.Request(url, headers=headers)
    raw = urllib.request.urlopen(req, timeout=60).read()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(raw)
    # 压缩 if needed（直接覆盖写出，避免 Windows 下 os.replace 权限问题；循环降质确保 <2MB）
    if len(raw) > 2 * 1024 * 1024:
        try:
            from PIL import Image
            im = Image.open(out_path)
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            w, h = im.size
            max_w = 1920
            if w > max_w:
                ratio = max_w / w
                im = im.resize((max_w, int(h * ratio)), Image.LANCZOS)
            q = 85
            while q >= 30:
                im.save(out_path, format="JPEG", quality=q, optimize=True)
                if os.path.getsize(out_path) <= 2 * 1024 * 1024:
                    break
                q -= 10
        except Exception as e:
            print(f"[warn] 压缩图片失败: {e}", file=sys.stderr)


def fetch_product_images(
    product_cfg: dict,
    ima_api_script: str,
    out_dir: str,
) -> Dict[str, Optional[str]]:
    """
    入口函数：根据产品配置抓取图片，返回 slot -> 本地文件路径。
    下载失败的 slot 会被跳过（值为 None）。
    """
    os.makedirs(out_dir, exist_ok=True)
    images = list_folder_images(
        product_cfg["kb_id"],
        product_cfg["folder_id"],
        ima_api_script,
    )
    selected = select_images(images, product_cfg.get("slots", []))
    results: Dict[str, Optional[str]] = {}
    for slot, item in selected.items():
        if not item:
            results[slot] = None
            continue
        ext_match = re.search(r"\.(png|jpe?g|gif|webp)$", item["title"], re.I)
        ext = (ext_match.group(1).lower() if ext_match else "png").replace("jpeg", "jpg")
        # 文件名安全化
        safe_title = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", item["title"])[:40]
        out_path = os.path.join(out_dir, f"{slot}_{safe_title}.{ext}")
        try:
            download_image(item["media_id"], out_path, ima_api_script)
            results[slot] = out_path
            print(f"[ima] {slot} -> {out_path} ({os.path.getsize(out_path)/1024:.0f}KB)", file=sys.stderr)
        except Exception as e:
            print(f"[ima] {slot} 下载失败: {e}", file=sys.stderr)
            results[slot] = None
    return results


def detect_product(topic: str, product_map: dict) -> Optional[str]:
    """
    根据主题关键词匹配产品。命中多个时取第一个（配置顺序优先）。
    """
    topic_lower = topic.lower()
    for product, cfg in product_map.items():
        for kw in cfg.get("topic_keywords", []):
            if kw.lower() in topic_lower:
                return product
    return None


if __name__ == "__main__":
    # 简单自测：抓取好业财图片
    import os
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(skill_dir, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(skill_dir, "config.example.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    product_cfg = cfg["product_image_map"]["好业财"]
    out_dir = os.path.join(skill_dir, "_ima_fetch_test")
    results = fetch_product_images(product_cfg, cfg["ima"]["ima_api_script"], out_dir)
    print(json.dumps({k: v for k, v in results.items() if v}, ensure_ascii=False, indent=2))
