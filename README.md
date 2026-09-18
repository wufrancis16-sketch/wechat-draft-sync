# wechat-draft-sync

> 面向 **SaaS 财务软件 / ERP / 进销存** 等垂直领域的微信公众号**内容生产 + 草稿同步**一体化技能。
> 从知识库取材 → AI 撰写 → 26 套主题配色排版 → 自动抓产品图 → 一键推到公众号草稿箱。

**同一个技能包，WorkBuddy 和 Codex 都能用** —— 因为 `SKILL.md` 是跨 Agent 的开放标准，两边都读它。差别只在**装在哪个目录、怎么唤起、以及执行环境（沙箱/审批）**。详见下方 [安装与使用：WorkBuddy vs Codex](#-安装与使用workbuddy-vs-codex)。

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

## 🖥 安装与使用：WorkBuddy vs Codex

一句话总览：**装的位置不同、唤起方式不同、权限模型不同，但命令和配置完全一样。**

### 对照表

| 维度 | **WorkBuddy** | **Codex CLI** |
|------|---------------|---------------|
| **用户级技能目录** | `~/.workbuddy/skills/<技能名>/` | `~/.agents/skills/<技能名>/`（官方 USER 位置）<br>`~/.codex/skills/`（即 `$CODEX_HOME/skills`，多数版本也认） |
| **项目/仓库级技能目录** | `<仓库>/.workbuddy/skills/` | `<仓库>/.agents/skills/`（Codex 从当前目录**逐级向上**一直扫到仓库根） |
| **唤起方式** | `/wechat-draft-sync` 斜杠命令，或 `@skill:wechat-draft-sync` | 先用 `/skills` 列出，再用 `$wechat-draft-sync ...` 点名；也可用自然语言让它按描述自动选中 |
| **技能识别依据** | `SKILL.md` 的 frontmatter（`name` + `description`） | 同上，`SKILL.md` 开放标准；可另加 `agents/openai.yaml`（Codex 专属元数据，可省略） |
| **项目常驻规则** | 无此机制（用技能 + `MEMORY.md`） | `AGENTS.md`：仓库根 / 各层目录，以及全局 `~/.codex/AGENTS.md` |
| **技能生效时机** | 保存即生效 | **代码改动后若没生效，重启 Codex**；技能元数据占上下文预算（超限会截断描述） |
| **脚本执行环境** | 本机直接执行 | **默认沙箱**（`workspace-write`）+ 审批策略，联网 / 写家目录 / 装依赖可能被拦 |
| **后台长任务** | 可直接后台跑脚本 | 非交互批处理用 `codex exec --full-auto "..."` |
| **Python 建议** | 用托管解释器，避免污染系统环境 | 用虚拟环境或 `uv`/`pyenv` 隔离 |
| **ima 脚本默认路径** | `~/.workbuddy/skills/ima-skills/ima_api.cjs` | `~/.agents/skills/ima-skills/ima_api.cjs`（**要改 `config.json`**） |

### 安装路径 A：WorkBuddy

```bash
git clone https://github.com/wufrancis16-sketch/wechat-draft-sync.git \
  ~/.workbuddy/skills/wechat-draft-sync
```

Windows 对应 `%USERPROFILE%\.workbuddy\skills\wechat-draft-sync`。

装好后在对话里用任一方式唤起：

```
/wechat-draft-sync 帮我写一篇 ERP 选型的公众号文章并同步草稿箱
```

```
@skill:wechat-draft-sync 写一篇进销存语音开单的文章，风格随机
```

### 安装路径 B：Codex CLI

```bash
# 0) 没装过 Codex CLI 的话（需要 Node.js）
npm install -g @openai/codex
codex --version

# 1) 装到官方 USER 技能目录
git clone https://github.com/wufrancis16-sketch/wechat-draft-sync.git \
  ~/.agents/skills/wechat-draft-sync
```

如果你的 Codex 版本是从 `~/.codex/skills/` 读技能的（`$CODEX_HOME/skills`），**用软链接一处管理、两处可用**（Codex 官方支持符号链接的技能目录）：

```bash
# macOS / Linux
mkdir -p ~/.codex/skills
ln -s ~/.agents/skills/wechat-draft-sync ~/.codex/skills/wechat-draft-sync
```

```bat
:: Windows（cmd，/J 建目录联接，不需要管理员权限）
mkdir "%USERPROFILE%\.codex\skills" 2>nul
mklink /J "%USERPROFILE%\.codex\skills\wechat-draft-sync" "%USERPROFILE%\.agents\skills\wechat-draft-sync"
```

在 Codex 里唤起：

```
/skills                                     # 先确认技能被识别
$wechat-draft-sync 写一篇 ERP 选型的公众号文章并同步草稿箱
```

> 兜底方案：如果你用的是带自定义斜杠命令的旧版 Codex，可以在 `~/.codex/prompts/wechat-draft.md` 里写一段自包含提示词（含技能目录路径与调用命令），然后用 `/wechat-draft` 触发；改完需重启 Codex。

### ⚠️ Codex 用户必读：沙箱与联网

这个技能要**联网**（`api.weixin.qq.com`、`ima.qq.com`）、要**写家目录**（`~/.config/ima/` 凭证、临时图片、封面 PNG）。Codex 默认沙箱会拦住这些动作，表现为请求超时、`Permission denied`、或反复弹审批。

推荐在 `~/.codex/config.toml` 里放开（**字段名以你的 Codex 版本为准**）：

```toml
approval_policy = "on-request"
sandbox_mode    = "workspace-write"

[sandbox_workspace_write]
network_access = true      # 联网：微信 / ima 接口必需
```

如果只是偶尔跑批，也可以在命令上临时放权：

```bash
codex exec --full-auto "用 wechat-draft-sync 技能同步 article.html 到公众号草稿箱"
```

> 还有一个小坑：`~/.config/ima/` 在部分沙箱策略下属于「家目录写」范围，会被拦。遇到就把它加进允许列表，或改用 `danger-full-access` 跑一次（谨慎，仅在自己的机器上）。

### 两端完全一致的部分（不用改）

- **命令行调用**：`python scripts/sync_wechat_draft.py --appid ... --html ...`，两个宿主一模一样。
- **配置文件结构与字段**：同一份 `config.json` 换个路径就能用。
- **主题库、模板、占位符**：`themes.json` / `wechat_article_template.html` 与宿主无关。
- **踩坑经验**：下面 FAQ 里的问题（IP 白名单、ima 版本门禁、2MB 图片限制）两边都会遇到。

### 同一台机器两个宿主并存

最稳的做法是**各装一份**（Codex 侧可用软链接）：

```
~/.workbuddy/skills/wechat-draft-sync/     ← WorkBuddy 用
~/.agents/skills/wechat-draft-sync/        ← Codex 用（再软链到 ~/.codex/skills/）
```

两份的 `config.json` 各填一次（内容其实可以完全相同，注意 `ima.ima_api_script` 的路径按宿主调整即可）。

---

## 📁 目录结构

```
wechat-draft-sync/
├── SKILL.md                        # 技能说明（给 AI Agent 读的完整工作流）★两个宿主都读这个
├── README.md                       # 本文件
├── AGENTS.md                       # Codex 项目级常驻指引（WorkBuddy 会忽略）
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
  - 脚本按 `$NODE_BIN` → `which node` → `node` 三级回退查找，找不到时用环境变量指定：
    ```bash
    NODE_BIN=/usr/local/bin/node python scripts/sync_wechat_draft.py ...
    ```
- **中文字体**：封面/Banner 渲染需要系统中文字体（Windows 用 `msyhbd.ttc` / `msyh.ttc` / `simhei.ttf`）
- 网络需可访问 `api.weixin.qq.com`（微信）与 `ima.qq.com`（知识库）
- 一个已认证的**微信公众号**，拿到 `AppID` 与 `AppSecret`

> **Codex 用户注意**：上面第一条依赖安装、以及所有网络请求，都需要沙箱放行（见上文「Codex 用户必读」）。

---

## 🚀 快速开始

### 1. 安装到技能目录

- **WorkBuddy** → `~/.workbuddy/skills/wechat-draft-sync`（见 [路径 A](#安装路径-aworkbuddy)）
- **Codex CLI** → `~/.agents/skills/wechat-draft-sync`（见 [路径 B](#安装路径-bcodex-cli)）

### 2. 生成配置文件

```bash
cd <你的技能目录>
cp config.example.json config.json
```

然后按下方「配置说明」填好 `config.json`。**`config.json` 已在 `.gitignore` 中，不会被提交。**

> **Codex 用户**记得把 `ima.ima_api_script` 改成 `~/.agents/skills/ima-skills/ima_api.cjs`。

### 3. 配置公众号 IP 白名单

先随便跑一次，报错里会带你的出口 IP：

```
40164 invalid ip 1.2.3.4, not in whitelist
```

到 **公众平台 → 设置与开发 → 基本配置 → IP白名单** 把它加进去。
⚠️ 复制粘贴容易带隐藏字符，建议**手动键入** IP；并确认白名单属于同一个 `appid`。

### 4. 同步一篇文章

两个宿主都是同一条命令：

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
| `ima.ima_api_script` | 抓图必填 | `ima_api.cjs` 的路径<br>WorkBuddy：`~/.workbuddy/skills/ima-skills/ima_api.cjs`<br>Codex：`~/.agents/skills/ima-skills/ima_api.cjs` |
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
<summary><b>两个宿主我该选哪个？</b></summary>

只要能用就行，功能完全一致。差别在于：WorkBuddy 的沙箱更宽松，开箱即跑；Codex 默认沙箱+审批更严格，需要按上文放开联网与家目录写入。若两个都在用，各装一份即可。
</details>

<details>
<summary><b>Codex 里 <code>/skills</code> 看不到这个技能</b></summary>

① 确认目录是 `~/.agents/skills/wechat-draft-sync/SKILL.md`（也可在 `~/.codex/skills/`）——**文件名必须正好是 `SKILL.md`**；② 用 `echo $CODEX_HOME` 确认技能根目录是否被改过；③ **重启 Codex**；④ 装了很多技能时描述会被截断，可先用 `$wechat-draft-sync` 显式点名。
</details>

<details>
<summary><b>Codex 里脚本报网络超时 / Permission denied</b></summary>

沙箱拦了联网或家目录写入。按「Codex 用户必读」在 `~/.codex/config.toml` 打开 `network_access` 与放宽 `sandbox_mode`，或临时用 `codex exec --full-auto`。
</details>

<details>
<summary><b>40164 invalid ip —— IP 不在白名单</b></summary>

把报错里的出口 IP 加到公众号「设置与开发 → 基本配置 → IP白名单」，**手动键入**避免粘贴带入隐藏字符，确认与 `appid` 对应后保存即可。
</details>

<details>
<summary><b>抓不到产品图 / 0 张图</b></summary>

依次检查：① ima 凭证（`~/.config/ima/client_id`、`~/.config/ima/api_key`）是否过期；② `folder_id` 是否变动；③ 图片标题是否能被 `slots[].pick` 关键词命中；④ `--topic` 里的关键词是否误命中了另一个产品；⑤ `ima.ima_api_script` 路径是否对应当前宿主的安装位置（**Codex 上最常见的坑**）。
</details>

<details>
<summary><b>ima 技能报版本门禁（code -200）</b></summary>

错误形如 `发现新版本 skill：1.1.x（当前 1.1.y）`，会中断当次同步。下载
`https://app-dl.ima.qq.com/skills/ima-skills-<新版本>.zip`，解压后把内容覆盖到对应宿主的
`ima-skills/` 目录（含 `notes/`、`knowledge-base/` 子目录）即可，CLI 调用约定不变。
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
