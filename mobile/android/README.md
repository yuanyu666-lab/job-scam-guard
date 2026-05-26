# 招聘防骗 · Android 悬浮框选版

类似 **夸克搜题** 的交互：系统级悬浮球 → 授权录屏 → 全屏框选 → 截图上传云端 → 返回风险结论。  
**不依赖与电脑同一 WiFi**，手机通过 **HTTPS 公网** 访问你部署的服务。

## 夸克大致怎么做（对标）

| 步骤 | 夸克 / 本 App |
|------|----------------|
| 悬浮窗 | `SYSTEM_ALERT_WINDOW` + `WindowManager` 悬浮球 |
| 截屏 | `MediaProjection`（系统录屏授权，非 root） |
| 框选 | 全屏半透明蒙层 + 手指拖矩形（与电脑版 `RegionSelector` 同类） |
| 识别 | 本方案：**云端 OCR**（服务器 `POST /api/analyze/image`） |
| 结论 | 悬浮结果条 / 结果页 |

部分搜题 App 还会用 **无障碍读屏** 取文字；招聘 JD 排版复杂，本方案以 **截图 + OCR** 为主，与电脑框选一致。

## Vivo X300 Pro（OriginOS）必开权限

1. **设置 → 应用 → 招聘防骗 → 权限**
   - 悬浮窗 / 后台弹出界面：**允许**
   - 通知：**允许**（Android 13+ 录屏前台服务需要）
2. 首次点悬浮球 → 允许 **整个屏幕录制 / 投屏**（MediaProjection 系统对话框）
3. 若悬浮球不显示：设置里搜 **「悬浮窗」** 或 **「显示在其他应用上层」**

## 一、部署云端 API（必做）

手机不能连电脑局域网时，需把 Python 服务放到 **公网 HTTPS**：

```bash
# 示例：云服务器
pip install -r requirements.txt
# 配置 data/deepseek_config.json、mobile_api.json 等
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

前面加 **Nginx + HTTPS** 或 Cloudflare Tunnel，得到例如：`https://job-guard.example.com`

可选安全：复制 `data/mobile_api.json.example` → `mobile_api.json`，设置 `api_token`；App 里填同一 Token。

自检：

```bash
curl https://你的域名/api/mobile/status
curl -X POST https://你的域名/api/analyze -H "Content-Type: application/json" -d "{\"text\":\"日结300加微信\"}"
```

## 二、编译安装 App

**详细图文步骤见：[制作APP教程.md](./制作APP教程.md)**（Vivo / 夸克式悬浮球）

简要：

1. 安装 [Android Studio](https://developer.android.com/studio)
2. 打开目录 `mobile/android`
3. 用 USB 调试连接 Vivo 手机，或生成 APK：**Build → Build APK**
4. 首次打开 App：
   - 填写 **服务器地址**（`https://...`，不要末尾 `/`）
   - 填写 **API Key**（若服务端启用了 token）
   - 点 **授权悬浮窗**、**授权屏幕录制**
   - 点 **启动悬浮球**
5. 在 BOSS / 微信等界面点悬浮球 → 框选文字区域 → 等待结果

## 三、与电脑版差异

| 项目 | 电脑悬浮窗 | 手机 App |
|------|------------|----------|
| 网络 | 本机 | 公网 HTTPS |
| OCR | 本机 Paddle/Rapid | 服务器 OCR |
| 框选 | 双击悬浮球 | 点悬浮球后框选 |
| 离线 | 可本地规则 | 需联网（符合你的要求） |

## 四、故障排查

- **401**：API Key 与服务端 `mobile_api.json` 不一致  
- **识别失败**：框选区域太小、模糊，尽量框住完整 JD  
- **上传慢**：图片会上传到服务器，首包 OCR 可能 10～30 秒  
- **悬浮球消失**：OriginOS 省电策略可能杀后台，在电池设置里允许后台运行  

## API 接口

- `POST /api/analyze/image` — `multipart/form-data`，字段 `file`（PNG/JPEG）  
- Header 可选：`X-API-Key`  
- 返回与 `/api/analyze` 相同，另含 `ocr_text_preview`
