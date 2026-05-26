# 招聘防骗（个人本地版）

粘贴招聘 JD 或聊天记录，本地规则检测风险。数据不出本机。

## 迁移到 D 盘（项目约 1GB，主要在 `.venv`）

1. **关掉** 悬浮窗和 Cursor  
2. **推荐轻量**：双击 **`迁移到D盘-轻量.bat`**（只复制代码，约几十 MB）→ 到 `D:\job-scam-guard` 后运行 **`首次安装依赖.bat`**  
3. **完整迁移**：双击 **`迁移到D盘.bat`**（含虚拟环境，约 1GB）  
4. 在 Cursor 里 **打开文件夹** → `D:\job-scam-guard`  
5. 确认无误后，按脚本提示删除 C 盘旧目录  

目标路径可在 `迁移到D盘.ps1` 里改 `$Dest`（默认 `D:\job-scam-guard`）。

## 手机版（Vivo / Android 悬浮框选）

**两步都卡了？先看：[一条龙-手机防骗.md](一条龙-手机防骗.md)**（免买服务器 + GitHub 打 APK）

类似夸克：**悬浮球 → 框选 → 云端 OCR + 检测**（不需与电脑同一 WiFi，需 **公网 HTTPS 服务器**）。

1. 将本项目 API 部署到云服务器（见 `mobile/android/README.md`）
2. 用 Android Studio 打开 `mobile/android` 编译安装 APK
3. App 内填写服务器地址 → 授权悬浮窗与录屏 → 启动悬浮球

备用：手机浏览器打开 `https://你的域名/mobile` 可粘贴文字检测。

## 悬浮窗（推荐，框选识图）

双击 **`启动悬浮窗.bat`**，或 `python run.py --float`

| 操作 | 说明 |
|------|------|
| **双击悬浮球** | 全屏框选 → OCR（RapidOCR）→ 风险检测 |
| **框选** | 拖动鼠标圈出招聘/聊天文字区域 |
| **粘贴检测** | 面板里用剪贴板文字检测（备用） |
| **Ctrl+Alt+J** | 展开 / 收起 |
| **Esc** | 取消框选 / 收起面板 |

### 框选识别（OCR）

默认 **`ocr_engine: fast`**（RapidOCR，轻量）。要最强中文可改为 `paddle` 或 `auto`（Paddle 优先）。

设置里可开 **OCR 后自动纠错**；识别失败会提示改用 **粘贴检测**。

## 云端 AI：DeepSeek / Gemini（可选）

默认推荐 **DeepSeek**（国内访问稳、性价比高）。也可继续用 **Gemini 3.1 Pro**。

### DeepSeek 配置

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 申请 API Key  
2. 复制 `data/deepseek_config.json.example` → `data/deepseek_config.json`，填入 `api_key`  
3. 复制 `data/ai_config.json.example` → `data/ai_config.json`，确认 `"provider": "deepseek"`  
4. 重启悬浮窗；「云端 AI」选 **deepseek**  

自检：双击 `测试DeepSeek.bat`（或 `POST /api/deepseek/test`），返回 `"ok": true` 即可。

要更强推理可把 `model` 改为 `deepseek-reasoner`（更慢、更贵）。

### Gemini 3.1 增强（可选）

在本地规则之上，可调用 Google **Gemini 3.1 Pro** 做二次研判（需联网、按 API 计费）。

### 重要：你买的「Gemini Pro」和本工具用的是两套东西

| 你开通的 | 本工具用的 |
|---------|-----------|
| gemini.google.com / Google One 里的 **Gemini Advanced** | [Google AI Studio](https://aistudio.google.com/) 的 **API Key + 项目计费** |

网页版 Pro **不会自动**给 API Key 付费额度。要在 AI Studio 里：

1. 打开 **Settings → Billing**，把计费账号绑到 **生成 Key 的那个项目**  
2. 确认 Rate limits 页显示 **Paid**（不是仅 Tier 1 免费）  
3. **计费生效后** 在同一项目 **重新生成 API Key**，写入 `data/gemini_config.json`  
4. 建议 `"allow_fallback": false`，只打 `gemini-3.1-pro-preview`，避免一次检测连打 3 个模型浪费配额  

配置步骤：

1. [申请 / 管理 API Key](https://aistudio.google.com/apikey)  
2. 复制 `data/gemini_config.json.example` → `gemini_config.json`，填 `api_key`  
3. `pip install google-genai`  
4. 悬浮窗勾选 **「Gemini 增强」**  

自检：启动 `python run.py` 后浏览器访问 `POST http://127.0.0.1:8765/api/gemini/test`（或用 curl），返回 `"ok": true` 即接通。

若仍 `429`：在 AI Studio 查看 **Usage / Spend cap** 是否触顶；等 1 分钟再试（程序会自动重试 2 次）。

## 网页版（可选）

```powershell
python run.py
```

打开 http://127.0.0.1:8765

## 查企业（免费跳转）

识别到公司名后，会出现 **天眼查 / 企查查 / 爱企查** 按钮，点击即在浏览器打开该公司搜索页，人工查看：

- **实缴资本**（认缴≠实缴）
- **参保人数**（年报或平台摘要）

无需付费 API。

## 改规则

编辑 `data/patterns.json` 后：

- 悬浮窗 **右键 → 重载规则**，或 `POST /api/patterns/reload`
- 也可重启 `python run.py`

`platform_packs` 可按 BOSS / 智联 / 微信私聊场景开关（设置里勾选）。

## 严格模式与 AI 策略

- 默认 **严格筛查** 开启；低危界面显示 **警惕**（非安全背书）
- `strict_ai_trigger`：`smart`（默认，省额度）| `always` | `borderline` | `high_risk_only`
- 本地已 **高危 ≥88 分** 时跳过云端 AI
- 悬浮窗 **⚙ 设置** 可改严格模式、OCR、历史、平台包

## 工商摘要解析

粘贴 **天眼查 / 企查查** 摘要页文字（含参保人数、实缴、经营异常等）再检测，会自动解析并加分。

## 核查清单与反馈

- **复制核查清单**：生成可打勾的核实项到剪贴板
- **误报反馈**：写入 `data/feedback.jsonl`，便于日后调规则
- 检测详情含 **评分明细**（各类命中权重）

## 本地记录

- **最近检测**：浏览器 localStorage，点标签可重新检测
- **记一笔**：写入 `data/notes.jsonl`，可用记事本查看

## API（自用）

- `POST /api/analyze` — 文本检测（body 可加 `"use_ai": true`）
- `GET/PATCH /api/settings` — 读写设置
- `POST /api/patterns/reload` — 热重载规则
- `POST /api/feedback` — 误报/漏报反馈
- `POST /api/checklist` — 生成核查清单文本
- `GET /api/history?q=` — 历史搜索
- `GET /api/history/export` — 导出 Markdown
- `GET /api/gemini/status` — Gemini 是否已配置
- `POST /api/analyze/url` — 链接检测
- `POST /api/note` — 本地备忘
- `GET /api/notes` — 最近备忘
