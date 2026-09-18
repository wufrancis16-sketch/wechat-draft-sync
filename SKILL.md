---
name: wechat-draft-sync
description: Sync a finished WeChat Official Account article (markdown or styled HTML) into the draft box via the official API. Handles access_token, cover upload, markdown→HTML, and the IP-whitelist pitfall (errcode 40164). NEW: a 26-theme color library (themes.json) that auto-matches the cover, top banner, section badges, highlight boxes, and the ending CTA card; a theme-colored banner generator; and an ima knowledge-base ingestion step that pulls domain material before AI drafting. Use when the user wants to "自动同步到公众号草稿箱", "push/publish an article to WeChat", "写公众号文章", or "按主题/配色写一篇并同步".
agent_created: true
---

# WeChat Draft Sync（公众号文章撰写 + 草稿同步）

## Overview
面向「SaaS 财务软件 / ERP / 进销存」等垂直领域公众号的内容生产 + 草稿同步一体化技能。一个完整流程包含：

1. **ima 知识库取材**（每次写新主题时主动触发）：从用户的 ima 知识库检索与主题相关的素材，作为 AI 撰写的事实依据。
2. **AI 撰写**：基于知识库素材 + 通用能力，产出符合公众号调性的长文。
3. **风格化排版**：套用可复用模板，并选定一套主题配色（26 选 1），文章风格与封面/Banner 自动搭配。
4. **自动产品配图**：根据文章主题匹配用友产品（好业财 / 好会计 / 好生意 / 易代账），从 ima 对应产品图片素材文件夹自动抓取截图，上传到微信并嵌入文章。
5. **同步草稿**：通过官方 `draft/add` 把文章 + 封面上传至公众号草稿箱。

## When to use
- 用户要求写一篇公众号文章并同步草稿（尤其 ERP / 财务软件 / 进销存 / 业财一体等垂直主题）。
- 用户要求「换风格 / 换配色 / 换封面」重排已有文章。
- 用户要求把 markdown 或自定义 HTML 推送到公众号草稿箱。
- 用户提到某个选题，希望「先看看我知识库里有没有相关内容再写」。

## Dependencies
- Python 3 with `requests`、`markdown`、`Pillow`：`pip install requests markdown Pillow`。
- 已安装并配置好 `ima-skills`：凭证在 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`；脚本路径在 `config.json` 的 `ima.ima_api_script`。
- 网络需能访问 `api.weixin.qq.com`（微信）与 `ima.qq.com`（知识库）。
- 封面/Banner 生成需要 Windows 中文字体（msyhbd.ttc / msyh.ttc / simhei.ttf）。

---

## Workflow（标准全流程）

### 第 0 步：ima 知识库取材（每次写新主题必做）
当用户提出一个写作主题时，**先不要直接开写**，而是先到 ima 知识库检索相关素材：

1. **确认 ima 凭证已配置**（已配置，凭证在 `~/.config/ima/client_id` 与 `~/.config/ima/api_key`）。检查命令：
   ```bash
   test -f ~/.config/ima/client_id && test -f ~/.config/ima/api_key && echo "✅ ima 凭证已配置" || echo "⚠️ 需配置 ima 凭证"
   ```
2. **用 `ima_api.cjs` 检索素材**（脚本路径见 `config.json` 的 `ima.ima_api_script`；接口统一在 `openapi/wiki/v1/` 下，注意不是顶层文档里写的 `openapi/list_*` 那些 404 路径）：
   ```bash
   IMA="$HOME/.workbuddy/skills/ima-skills/ima_api.cjs"
   OPTS=$(printf '{"clientId":"%s","apiKey":"%s"}' "$(cat ~/.config/ima/client_id)" "$(cat ~/.config/ima/api_key)")
   KB="<你的主知识库ID>"   # 小白知识库（主素材库，见 config.json ima.primary_kb.id）

   # 1) 看自己有哪些知识库（query 传空字符串）
   node "$IMA" "openapi/wiki/v1/search_knowledge_base" '{"query":"","cursor":"","limit":20}' "$OPTS"

   # 2) 在《小白知识库》里搜主题相关素材（按标题/文件名匹配，多试几个同义词）
   node "$IMA" "openapi/wiki/v1/search_knowledge" '{"query":"用友好会计","knowledge_base_id":"'"$KB"'","cursor":""}' "$OPTS"

   # 3) 取某条素材的原文（media_id 来自上面的搜索/列表结果）
   node "$IMA" "openapi/wiki/v1/get_media_info" '{"media_id":"<media_id>"}' "$OPTS"
   #    - media_type=11（笔记）：用返回的 notebook_id 调 notes 模块 get_doc_content 取正文
   #    - 其余（文件/网页）：用返回的 url_info.url 请求原文
   ```
   > 主素材库默认《小白知识库》（60 条，含「用友好会计/好业财/好生意/易代账」产品夹、「小红书运营经验」「公众号爆款选题」「种草夸赞类」笔记等）。写小红书向内容可加搜《小红书知识库Pro》（`config.json` 的 `ima.secondary_kb.id`）。
3. 提炼出可引用的要点：产品卖点、客户案例、行业数据、常见痛点、爆款标题句式等。
4. **降级策略**：若 ima 凭证缺失或检索为空，则直接用 AI 通用能力撰写，并在交付时说明「本次未接入知识库，内容为通用撰写」。

> ima 的完整错误处理、UTF-8 规则见 `ima-skills` 技能文档；知识库接口路径以 `openapi/wiki/v1/` 为准（本技能已实测可用）。

### 第 1 步：撰写正文
- 结合「知识库素材 + AI 撰写」产出文章 markdown（或直接在模板里写 HTML）。
- 若产出 markdown，建议在文中用 `## 正文内容` 起头、`**核心观点**` 收尾，便于脚本精准提取正文（也可不加，脚本会回退全文）。

### 第 2 步：选主题配色
从下方 **主题配色库** 选一个 key（如 `blue` / `green` / `red` …）。文章的主色、浅底、封面底色、Banner 底色、结尾卡片颜色全部联动，无需手动调色。

### 第 3 步：套模板 / 写 HTML
- 直接复制 `wechat_article_template.html`，替换 `{{LEAD}}` `{{SECTION_TITLE}}` `{{SECTION_CONTENT}}` 等正文占位符。
- 模板已内置：
  - `{{BANNER_URL}}`（顶部 Banner，自动生成并替换）
  - `{{THEME_COLOR}}` `{{TINT_COLOR}}` `{{END_COLOR}}` `{{END_BG}}`（配色占位符）
  - `{{QR_URL}}` `{{WECHAT_ID}}`（结尾二维码）
  - `{{IMG_HERO}}` `{{IMG_OVERVIEW}}` `{{IMG_FLOW}}` `{{IMG_PROJECT}}` `{{IMG_CONTRACT}}` `{{IMG_FINANCE}}` `{{IMG_INVENTORY}}`（产品截图占位符；配合 `--auto-images --topic` 自动抓取替换）
- **结尾卡片「添加领取专属行业软件方案」默认自带**，每篇都保留，只换二维码和微信号。
- **最佳实践**：写 HTML 时把目标产品 `slots` 对应的占位符**全部放上**（如好业财放满 7 个、好生意 6 个、好会计 5 个），图片位置最精准；漏掉的图会走安全锚点兜底分散插入正文段落之后。

### 第 4 步：同步草稿
```bash
python scripts/sync_wechat_draft.py \
  --appid X --appsecret Y \
  --html article.html --title "标题" --author "SaaS财务软件" --digest "摘要" \
  --theme blue \
  --topic "ERP 业财一体 项目管理" \
  --auto-images         # 自动从 ima 抓取对应产品图并嵌入文章
```
- 省略 `--cover` 且有 `--theme` 时，脚本自动生成主题色封面。
- HTML 含 `{{BANNER_URL}}` 且有 `--theme` 时，脚本自动生成主题色 Banner 并上传替换。
- `--topic` 用于自动匹配产品（如 ERP/业财一体/项目管理 → 好业财），配合 `--auto-images` 抓取产品截图并嵌入。
- 二维码 URL 与微信号从 `config.json` 读取（首次搭建上传一次二维码永久素材后填入即可）。

---

## 自动产品配图（ima 图片素材抓取）

`config.json` 的 `product_image_map` 维护了一套「主题关键词 → 用友产品 → ima 图片素材文件夹」的映射：

| 产品 | 主题关键词示例 | ima 图片素材文件夹 |
|------|----------------|-------------------|
| 好业财 | ERP、业财一体、项目管理、项目合同、财务业务一体化 | 好业财图片素材 |
| 好会计 | 好会计、财务软件、做账、凭证、总账、资产负债表、智能做账 | 好会计图片素材 |
| 好生意 | 好生意、进销存、开单软件、出入库、库存管理、销售管理 | 好生意图片素材 |
| 易代账 | 易代账、代账软件、代理记账、代账、批量取票、智能审账 | 易代账图片素材 |

### 工作原理
1. `sync_wechat_draft.py --topic "文章主题"` 调用 `ima_media.detect_product()` 匹配产品。
2. 按该产品在 `product_image_map` 中的 `folder_id` 列出《小白知识库》对应文件夹下的所有图片。
3. 按 `slots` 规则挑选：例如 `hero` 优先选标题含「首页」的图，`project` 优先选标题含「项目看板/项目合同」的图。
4. 通过 `get_media_info` 拿到带签名的下载 URL，下载到本地临时目录。
5. 调用 `material/add_material` 上传为微信永久素材，拿到 `url`。
6. 有 `{{IMG_*}}` 占位符的按占位符精准替换（作者可控）；占位符装不下的图，均匀插入到**正文段落之后**（安全锚点，只用 `</p>` 末端，绝不使用裸字符偏移）；若一个正文段落都没有，则插到最后一个 `</div>` 之前。
7. 发布前自动体检 `check_html_integrity()`：标签被切坏 → 直接阻止同步并报错；仍有未替换占位符 → 打警告。

> ⚠️ **历史 bug（已修，勿回退）**：早期 fallback 用 `h2_positions[0] + len("</h2>")` 作为插入位置，文章里没有 `</h2>` 时会退化成 `0 + 5`，把首行 `<div style="font-size:16px;…">` 切成 `<div <p>…图…</p>style="font-size:16px;…">`。微信编辑器再把它规范化成 `<div p="p" style="…">`，结果**文章开头多出几张产品图 + 一行裸露的 code（`style="…">`）**。现在插图只走安全锚点，并有体检兜底。

### 扩展/修正映射
- 新增产品：在 `config.json` 的 `product_image_map` 中追加一个 key，填入 `folder_id`（可用 `openapi/wiki/v1/get_knowledge_list` 查）、`topic_keywords` 和 `slots`。
- 调整选图偏好：修改对应产品 `slots[].pick` 数组里的标题关键词（脚本按顺序匹配第一条命中的）。
- 图片超过 2MB：脚本会自动压缩到 1920 宽、JPEG 质量 85，确保微信永久素材接口可接受。

### 常见问题
- **抓取失败 / 0 张图**：检查 ima 凭证是否过期、文件夹 ID 是否变动、图片标题是否与 `slots[].pick` 匹配。
- **`ima_api error: {"code":-200,...发现新版本 skill：1.1.x}`**：ima 技能有版本门禁。下载 `https://app-dl.ima.qq.com/skills/ima-skills-<新版本>.zip`，解压后把 `ima_api.cjs` / `meta.json` / `SKILL.md`（含 `notes/`、`knowledge-base/`）覆盖到 `~/.workbuddy/skills/ima-skills/` 即可（脚本按 `meta.json` 里的 version 上报，无需改代码）。
- **草稿开头多出图片 + 一行 code**：见上方历史 bug；已修，若复现先确认 `insert_product_images` 没被改回裸偏移插入。
- **想放非产品图**：关闭 `--auto-images`，手动在 HTML 里用 `<img>` 引用已上传的微信图片 URL。

### 同步后核验（建议每次批量同步后做）
用 `draft/batchget`（`no_content: 0`）拉回草稿，检查每条 content 的**首部**是否以 `<div style="font-size:16px;` 开头、且不含 `<div p="p"` 这种畸形标签；发现畸形可见即 `draft/delete` 删掉重发。注意：微信会把 `src` 改写成 `data-src`，本地预览时需还原。

---

## 主题配色库（themes.json，26 套，随时切换）
每套含 `theme`(主色/徽章/高亮文字) `tint`(浅底) `cover_bg`(封面) `banner_bg`(Banner) `end_color`/`end_bg`(结尾卡片)。在 `sync_wechat_draft.py --theme <key>` 或 `gen_cover.py --theme <key>` / `gen_banner.py --theme <key>` 中引用。

| key | 名称 | 主色 | key | 名称 | 主色 |
|-----|------|------|-----|------|------|
| blue | 科技蓝 | #1E5BFF | navy | 藏青 | #0D47A1 |
| red | 中国红 | #E63946 | violet | 紫罗兰 | #8E24AA |
| green | 自然绿 | #11998E | crimson | 绯红 | #C62828 |
| purple | 优雅紫 | #7B1FA2 | deepblue | 深蓝 | #1565C0 |
| orange | 活力橙 | #F57C00 | coral | 珊瑚橙 | #FF7043 |
| teal | 青碧 | #00897B | moss | 苔绿 | #558B2F |
| pink | 少女粉 | #D81B60 | magenta | 洋红 | #AD1457 |
| indigo | 靛蓝 | #3949AB | steel | 钢蓝 | #455A64 |
| cyan | 湖蓝 | #0097A7 | sky | 天空蓝 | #0288D1 |
| amber | 琥珀黄 | #FF8F00 | limegreen | 青柠 | #7CB342 |
| deepred | 酒红 | #B71C1C | lime | 柠檬绿 | #689F38 |
| brown | 沉稳棕 | #6D4C41 | rose | 玫红 | #E91E63 |
| blackgold | 黑金 | #1A1A1A | slate | 石墨灰 | #37474F |

> 想新增风格：在 `themes.json` 追加一个 key 即可，脚本无需改动。

---

## Body extraction
`--md` 模式下，脚本默认提取 `## 正文内容` 与 `**核心观点**` 之间的内容；无标记时回退全文。调整正则见 `scripts/sync_wechat_draft.py`。

## Critical pitfall: IP whitelist (errcode 40164)
首次调用常报 `40164 invalid ip ... not in whitelist`。把报错里的出口 IP 加到 设置与开发 → 基本配置 → IP白名单。
- **复制粘贴易带入隐藏字符**，务必手敲 IP 后保存。
- 确认白名单属于同一 `appid`。
- 正确保存后重试立即生效。

## Styling
- `--md` 模式：容器 `font-size:16px; line-height:2`；`<strong>` 与 `<h2>`–`<h4>` 放大到 17px。
- `--html` 模式：文件原样作为 `content`，完全自定义；图片需先上传拿 `url` 再引用。
- **微信会过滤大量 CSS**：`<div>` 背景色、`border-radius`、表格单元格背景常被剥。因此 Banner 做成图片、正文用 `<p>`/`<span>`/`<table>` 内联样式、章节徽章用矩形色块。

## Cover generation（gen_cover.py）
```bash
python scripts/gen_cover.py --title "标题文字" --out cover.png [--theme blue] [--bg #RRGGBB]
```
- `--theme` 从 `themes.json` 取封面底色；`--bg` 直接指定；都不给则随机。
- 字号自适应：≤10 字单行，>10 字按 10 字换行，始终居中。输出 900×383。

## Banner generation（gen_banner.py）
```bash
python scripts/gen_banner.py --title "主标题" --subtitle "副标题" --out banner.png [--theme blue]
```
- 900×320，主题色背景 + 半透明装饰圆 + 白色居中标题；标题字号自适应。
- 同步流程中，`--theme` 会自动生成并上传 Banner 替换 HTML 里的 `{{BANNER_URL}}`。

## Notes
- `draft/add` 只建草稿，群发需在后台手动操作（受服务号频次限制）。
- `access_token` 有效期 7200s，脚本每次重新获取。
- 结尾卡片「添加领取专属行业软件方案」为每篇默认自带模块，颜色跟随主题。

## Resources
- `scripts/sync_wechat_draft.py` — 同步脚本（支持 `--theme` 自动生成封面/Banner、`--auto-images --topic` 自动抓图）。
- `scripts/ima_media.py` — ima 图片素材抓取与下载模块。
- `scripts/gen_cover.py` — 封面生成（支持 `--theme`）。
- `scripts/gen_banner.py` — 主题色 Banner 生成（支持 `--theme`）。
- `themes.json` — 26 套风格配色库。
- `config.json` — 二维码、微信号、默认主题、产品图片映射。
- `references/wechat_api_notes.md` — 微信接口与 errcode 速查。
- `wechat_article_template.html`（工作区产出）— 可复用文章模板。
