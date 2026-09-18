# wechat-draft-sync

> 面向 **SaaS 财务软件 / ERP / 进销存** 等垂直领域的微信公众号**内容生产 + 草稿同步**一体化技能。
> 从知识库取材 → AI 撰写 → 26 套主题配色排版 → 自动抓产品图 → 一键推到公众号草稿箱。

---

## ✨ 能力一览

| 能力 | 说明 |
|------|------|
| **知识库取材** | 写新主题前先从 ima 知识库检索素材，作为撰写的事实依据（避免空对空输出） |
| **26 套主题配色** | `themes.json` 内置 26 套配色，正文主色 / 浅底 / 封面 / Banner / 结尾卡片**全部联动**，`--theme` 一键切换 |
| **自动封面 + Banner** | 主题色封面（900×383）与文章顶部 Banner（900×320）自动生成并上传，标题**自动折行 + 字号自适应**，不重叠 |
| **自动产品配图** | 按文章主题匹配产品（ERP/业财一体/项目管理 → 好业财；财务/做账 → 好会计；进销存/开单 → 好生意；代账 → 易代账），从知识库图片素材夹自动抓图、压缩、上传并嵌入正文 |
| **固定结尾卡片** | 「添加领取专属行业软件方案」二维码卡片每篇默认自带，颜色跟随主题 |
| **发布前体检** | 同步前自动校验 HTML 完整性，标签被切坏直接拦截，避免发出畸形草稿 |

---

## 📁 目录结构

```
wechat-draft-sync/
├── SKILL.md                        # 技能说明（给 AI Agent 读的完整工作流）
├── README.md                       # 本文件
├── config.example.json             # 配置模板（复制为 config.json 后填写）
├── themes.json                     # 26 套主题配色库
├── wechat_article_template.html    # 文章模板（含 Banner / 配图 / 配色占位符）
├── references/
│   └── wechat_api_notes.md         # 微信接口与 errcode 速查
└── scripts/
    ├── sync_wechat_draft.py        # 主同步脚本（封面/Banner/配图/草稿）
    ├── ima_media.py                # 知识库图片抓取与下载模块
    ├── gen_cover.py                # 封面生成（主题色 / 字号自适应）
    └── gen_banner.py               # Banner 生成（自动折行，防重叠）
```

---

## 🔧 环境要求

- **Python 3.8+**，依赖：`requests`、`markdown`、`Pillow`
  ```bash
  pip install requests markdown Pillow
  ```
- **Node.js**（仅在使用「自动抓产品图」时需要，用于调用 ima 知识库 CLI）
- **中文字体**：封面/Banner 渲染需要系统中文字体（Windows 用 `msyhbd.ttc` / `msyh.ttc` / `simhei.ttf`）
- 网络需可访问 `api.weixin.qq.com`（微信）与 `ima.qq.com`（知识库）
- 一个已认证的**微信公众号**，拿到 `AppID` 与 `AppSecret`

---

## 🚀 快速开始

### 1. 安装到技能目录

```bash
git clone https://github.com/wufrancis16-sketch/wechat-draft-sync.git \
  ~/.workbuddy/skills/wechat-draft-sync
```

Windows 路径为 `%USERPROFILE%\.workbuddy\skills\wechat-draft-sync`。

### 2. 生成配置文件

```bash
cd ~/.workbuddy/skills/wechat-draft-sync
cp config.example.json config.json
```

然后按下方「配置说明」填好 `config.json`。**`config.json` 已在 `.gitignore` 中，不会被提交。**

### 3. 配置公众号 IP 白名单

先随便跑一次，报错里会带你的出口 IP：

```
40164 invalid ip 1.2.3.4, not in whitelist
```

到 **公众平台 → 设置与开发 → 基本配置 → IP白名单** 把它加进去。
⚠️ 复制粘贴容易带隐藏字符，建议**手动键入** IP；并确认白名单属于同一个 `appid`。

### 4. 同步一篇文章

```bash
python scripts/sync_wechat_draft.py \
  --appid  你的AppID \
  --appsecret 你的AppSecret \
  --html article.html \
  --title "文章标题" \
  --author "作者名" \
  --digest "摘要文字" \
  --theme blue \
  --topic "ERP 业财一体 项目管理" \
  --auto-images
```

跑完控制台会输出草稿 `media_id` 和封面 `media_id`，到公众号后台「草稿箱」即可看到。

---

## ⚙️ 配置说明（`config.json`）

| 字段 | 必填 | 说明 |
|------|:---:|------|
| `qr_url` | ✅ | 结尾卡片的二维码图片 URL。先把二维码上传为微信**永久素材**，或用任意公网可访问的图片地址 |
| `wechat_id` | ✅ | 结尾卡片显示的个人微信号 |
| `default_theme` | — | 不传 `--theme` 时使用的默认主题 key，默认 `blue` |
| `ima.primary_kb.id` | 抓图必填 | 主知识库 ID（`search_knowledge_base` 可查） |
| `ima.secondary_kb.id` | — | 副知识库 ID，可选 |
| `ima.ima_api_script` | 抓图必填 | `ima_api.cjs` 的路径，默认 `~/.workbuddy/skills/ima-skills/ima_api.cjs` |
| `product_image_map.<产品>.folder_id` | 抓图必填 | 该产品图片素材所在的知识库**文件夹 ID** |
| `product_image_map.<产品>.topic_keywords` | ✅ | 主题关键词，命中即选中该产品（**按配置顺序**匹配首个命中） |
| `product_image_map.<产品>.slots[].pick` | ✅ | 选图规则，按顺序匹配第一条命中的图片标题 |

> 💡 **关键词冲突提醒**：检测是「按顺序取首个命中」。若某关键词被两个产品共用（例如「进销存」同时出现在好业财和好生意里），会误命中排在前面的产品。请保证每个关键词只归属一个产品。

### 图片占位符（可选，推荐）

在 HTML 里放占位符可**精准控图**；不放则自动分散插入正文段落之后。

| 产品 | 可用占位符 |
|------|-----------|
| 好业财 | `{{IMG_HERO}}` `{{IMG_OVERVIEW}}` `{{IMG_FLOW}}` `{{IMG_PROJECT}}` `{{IMG_CONTRACT}}` `{{IMG_FINANCE}}` `{{IMG_INVENTORY}}` |
| 好会计 | `{{IMG_HERO}}` `{{IMG_AI}}` `{{IMG_REPORT}}` `{{IMG_INVOICE}}` `{{IMG_BANK}}` |
| 好生意 | `{{IMG_HERO}}` `{{IMG_SALES}}` `{{IMG_PURCHASE}}` `{{IMG_INVENTORY}}` `{{IMG_DATA}}` `{{IMG_AI}}` |
| 易代账 | `{{IMG_HERO}}` `{{IMG_AUTO}}` `{{IMG_AUDIT}}` `{{IMG_TAX}}` `{{IMG_ARCHIVE}}` |

> 建议把目标产品的占位符**全部放上**，图片位置最精准。

---

## 🎨 主题配色库（26 套）

`--theme <key>` 一键切换，文章与封面配色自动搭配。

| key | 名称 | 主色 | key | 名称 | 主色 |
|-----|------|------|-----|------|------|
| `blue` | 科技蓝 | `#1E5BFF` | `navy` | 藏青 | `#0D47A1` |
| `red` | 中国红 | `#E63946` | `violet` | 紫罗兰 | `#8E24AA` |
| `green` | 自然绿 | `#11998E` | `crimson` | 绯红 | `#C62828` |
| `purple` | 优雅紫 | `#7B1FA2` | `deepblue` | 深蓝 | `#1565C0` |
| `orange` | 活力橙 | `#F57C00` | `coral` | 珊瑚橙 | `#FF7043` |
| `teal` | 青碧 | `#00897B` | `moss` | 苔绿 | `#558B2F` |
| `pink` | 少女粉 | `#D81B60` | `magenta` | 洋红 | `#AD1457` |
| `indigo` | 靛蓝 | `#3949AB` | `steel` | 钢蓝 | `#455A64` |
| `cyan` | 湖蓝 | `#0097A7` | `sky` | 天空蓝 | `#0288D1` |
| `amber` | 琥珀黄 | `#FF8F00` | `limegreen` | 青柠 | `#7CB342` |
| `deepred` | 酒红 | `#B71C1C` | `lime` | 柠檬绿 | `#689F38` |
| `brown` | 沉稳棕 | `#6D4C41` | `rose` | 玫红 | `#E91E63` |
| `blackgold` | 黑金 | `#1A1A1A` | `slate` | 石墨灰 | `#37474F` |

新增风格只需在 `themes.json` 追加一个 key，脚本无需改动。

---

## 🖼 单独生成封面 / Banner

```bash
# 封面（900×383，≤10 字单行、超 10 字按 10 字换行，居中，字号自适应）
python scripts/gen_cover.py --title "ERP 选型避坑指南" --out cover.png --theme navy

# Banner（900×320，标题自动折行、整体垂直居中、与副标题不重叠）
python scripts/gen_banner.py --title "主标题" --subtitle "副标题" --out banner.png --theme navy
```

---

## ❗ 常见问题

<details>
<summary><b>40164 invalid ip —— IP 不在白名单</b></summary>

把报错里的出口 IP 加到公众号「设置与开发 → 基本配置 → IP白名单」，**手动键入**避免粘贴带入隐藏字符，确认与 `appid` 对应后保存即可。
</details>

<details>
<summary><b>抓不到产品图 / 0 张图</b></summary>

依次检查：① ima 凭证（`~/.config/ima/client_id`、`~/.config/ima/api_key`）是否过期；② `folder_id` 是否变动；③ 图片标题是否能被 `slots[].pick` 关键词命中；④ `--topic` 里的关键词是否误命中了另一个产品。
</details>

<details>
<summary><b>ima 技能报版本门禁（code -200）</b></summary>

错误形如 `发现新版本 skill：1.1.x（当前 1.1.y）`，会中断当次同步。下载
`https://app-dl.ima.qq.com/skills/ima-skills-<新版本>.zip`，解压后把内容覆盖到
`~/.workbuddy/skills/ima-skills/`（含 `notes/`、`knowledge-base/` 子目录）即可，CLI 调用约定不变。
</details>

<details>
<summary><b>草稿开头莫名多出几张图 + 一行 code</b></summary>

**历史 bug，已修复。** 早期版本插图兜底用 `</h2>` 位置偏移，而本模板不含 `</h2>`，导致偏移退化为第 5 个字符，把首行 `<div style="…">` 从中间切开，微信编辑器再规范化为 `<div p="p" style="…">`。

现在插图**只走安全锚点**（正文段落 `</p>` 之后），并有 `check_html_integrity()` 发布前体检兜底。若复现，请确认 `insert_product_images()` 没有被改回裸字符偏移插入。
</details>

<details>
<summary><b>同步后想核验草稿内容</b></summary>

用 `draft/batchget`（`no_content: 0`）拉回草稿，检查每条 `content` 首部是否以 `<div style="font-size:16px;` 开头、且不含 `<div p="p"` 这类畸形标签；发现畸形用 `draft/delete` 删掉重发。

注意：微信会把 `content` 里的 `src` 改写为 `data-src`，本地预览时需还原。
</details>

<details>
<summary><b>微信把样式吃掉了</b></summary>

微信会过滤大量 CSS：`<div>` 背景色、`border-radius`、表格单元格背景常被剥离。
因此本项目 Banner **做成图片**、正文统一用 `<p>` / `<span>` / `<table>` 内联样式、章节徽章用矩形色块。
</details>

---

## 📌 说明

- `draft/add` **只创建草稿**，群发需在公众号后台手动操作。
- `access_token` 有效期 7200 秒，脚本每次运行时重新获取。
- 本号若无 `freepublish` 权限，`freepublish/batchget` 会返回 `48001`，属正常现象，不影响草稿同步。
- 使用本技能需自行准备公众号、知识库与产品素材，请遵守微信平台规则，仅发布合规内容。

## License

未指定。如需授权他人使用，建议补充 `LICENSE`（如 MIT）。
