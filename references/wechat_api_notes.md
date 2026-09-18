# 微信公众号草稿同步 · API 要点与排错

## 涉及接口

| 用途 | 方法 | 端点 |
|------|------|------|
| 获取 access_token | GET | `https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET` |
| 上传永久素材（封面） | POST | `https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=TOKEN&type=image`（form-data: media） |
| 创建草稿 | POST | `https://api.weixin.qq.com/cgi-bin/draft/add?access_token=TOKEN`（body: `{"articles":[{...}]}`） |

## 关键限制

- **IP 白名单**：调用 token 接口的服务器公网 IP 必须在公众号「设置与开发 → 基本配置 → IP白名单」中。否则报 `40164`。
- **封面素材**：永久图片素材建议 ≤2MB；超出可能上传失败。
- **草稿正文 content**：HTML 字符串，建议 ≤20000 字；微信后台会做基础渲染。
- **草稿 vs 群发**：`draft/add` 仅入草稿箱，不能自动群发；群发需后台操作或另调 `masssend` 接口（受服务号频次限制）。

## access_token 说明

- 有效期 **7200 秒（2 小时）**，过期需重新获取。
- 每日获取上限约 2000 次；脚本每次运行现取现用，无需缓存。
- token 与 appid 绑定，不可跨号使用。

## errcode 速查

| errcode | 含义 | 处理 |
|---------|------|------|
| 40164 | invalid ip，不在白名单 | 将运行环境出口 IP 加入 IP白名单（手打，勿复制粘贴） |
| 40013 | appid 无效 | 检查 appid 是否正确 |
| 40001 / 40014 | appsecret 错误或无效 | 核对 appsecret；可在后台重置 |
| 42001 / 40014 | access_token 过期或非法 | 重新获取（脚本已自动） |
| 45009 | 接口调用超限 | 等待频次恢复 |
| 48001 | 接口未授权（号型不支持） | 确认公众号已认证且具备该接口权限 |

## 正文 HTML 提示

- markdown 转出的裸 HTML 基础可用；如需精致排版（分段配色、重点高亮），可在后台编辑器二次微调。
- 封面图若不含文字，标题文案建议在后台封面编辑区叠加，保证清晰可读。
