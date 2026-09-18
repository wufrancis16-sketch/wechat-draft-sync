# AGENTS.md

本仓库是一个 **Agent Skill**（微信公众号文章撰写 + 草稿同步），不是普通软件项目。
给 Codex 的常驻指引如下。

## 这个仓库怎么用

技能本体就是当前目录。使用前先装到宿主的技能目录，不要在仓库里直接跑生产同步。

| 宿主 | 安装位置 | 唤起方式 |
|------|----------|----------|
| Codex CLI | `~/.agents/skills/wechat-draft-sync/` 或 `~/.codex/skills/wechat-draft-sync/` | `/skills` 列出后 `$wechat-draft-sync <需求>` |
| WorkBuddy | `~/.workbuddy/skills/wechat-draft-sync/` | `/wechat-draft-sync` 或 `@skill:wechat-draft-sync` |

`SKILL.md` 是完整工作流说明，**改技能行为时以它为准**（README 面向人，`SKILL.md` 面向 Agent）。

## 常用命令

```bash
# 依赖（一次性）
pip install requests markdown Pillow

# 同步一篇文章到公众号草稿箱
python scripts/sync_wechat_draft.py \
  --appid <APPID> --appsecret <APPSECRET> \
  --html article.html --title "标题" --author "SaaS财务软件" --digest "摘要" \
  --theme <主题key> --topic "<产品关键词>" --auto-images

# 单独出图
python scripts/gen_cover.py  --title "封面标题" --out cover.png  --theme <key>
python scripts/gen_banner.py --title "主标题" --subtitle "副标题" --out banner.png --theme <key>
```

配置在 `config.json`（从 `config.example.json` 复制，**不要提交**）。

## Codex 环境下的硬性注意事项

1. **沙箱**：本技能必须联网（`api.weixin.qq.com`、`ima.qq.com`），且要写 `~/.config/ima/`、临时目录与 PNG 输出。Codex 默认 `workspace-write` 沙箱会拦住，需在 `~/.codex/config.toml` 打开：
   ```toml
   approval_policy = "on-request"
   sandbox_mode    = "workspace-write"

   [sandbox_workspace_write]
   network_access = true
   ```
2. **不要改 `SKILL.md` 的 frontmatter 触发词**（`name` / `description`）——Codex 靠 `description` 隐式选中技能，且描述可能被截断，关键触发词必须留在最前面。
3. 技能是**即读即用**的：`SKILL.md` 与脚本发到 GitHub 后，同事 `git pull` 即可更新，无需重新安装。
4. 改动脚本后如未生效，**重启 Codex**。

## 不要做的事

- **不要提交 `config.json`**（含二维码、微信号、知识库 ID），它已在 `.gitignore`。新增可提交的配置一律先进 `config.example.json` 并置空私有值。
- **不要在文章里写死真实品牌名**（用「这套 ERP」等模糊表达）——这是使用本技能的业务约定，见 `SKILL.md`。
- 不要在 `insert_product_images()` 里恢复「按字符偏移插图」的写法：本模板没有 `</h2>`，偏移会退化成第 5 个字符并切坏首行 `<div>`，导致草稿开头多出图片 + 一行裸露 code。当前实现只允许安全锚点（正文 `</p>` 之后），并有 `check_html_integrity()` 体检兜底。
- 不要改动微信接口的调用路径约定（`draft/add`、`material/add_material`）；`freepublish` 无权限返回 `48001` 属正常。

## 关键事实速查

- 主题库：`themes.json`，26 套，`--theme <key>` 联动正文/封面/Banner/结尾卡片。
- 产品配图映射：`config.json` → `product_image_map`，按 `topic_keywords` **顺序**匹配首个命中（关键词不能跨产品共用）。
- 图片占位符：`{{IMG_<SLOT>}}`，slot 来自目标产品的 `slots[].slot`；建议全部放上，位置最精准。
- 微信永久素材**单图上限 2MB**，超了脚本会自动压缩（1920 宽 / JPEG 降质）。
- 首次调用常报 `40164`（IP 白名单），需在公众号后台添加出口 IP，**手动键入**避免隐藏字符。
