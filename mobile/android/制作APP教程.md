# 招聘防骗 · 夸克式悬浮球 App 制作教程

面向 **Vivo X300 Pro（OriginOS）**，不需要手机和电脑同一 WiFi，但必须有一台 **公网 HTTPS 服务器** 跑检测 API。

---

## 整体要做什么（3 件事）

```
┌─────────────┐     HTTPS      ┌──────────────────┐
│  手机 App   │ ──────────────►│ 云服务器 API      │
│ 小悬浮球+框选│   上传截图      │ Python 招聘防骗服务 │
└─────────────┘                └──────────────────┘
        ▲
        │ 在电脑上用 Android Studio 编译出 APK 装到手机
```

1. **云端**：把项目里的 `app/main.py` 部署到公网（带 `https://`）  
2. **电脑**：用 Android Studio 打开 `mobile/android`，打出 APK  
3. **手机**：安装 APK → 填服务器地址 → 开悬浮球 → 像夸克一样用  

---

## 第一步：部署云端 API（手机能访问的网址）

### 你需要

- 一台有公网 IP 的云服务器（阿里云 / 腾讯云 / 轻量应用服务器均可），或  
- 本机 + **Cloudflare Tunnel** / **ngrok**（免买服务器，适合先试）

### 在服务器上（Linux 示例）

```bash
# 上传整个 job-scam-guard 项目到服务器
cd job-scam-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置（至少复制并填写 AI、可选 mobile_api）
cp data/mobile_api.json.example data/mobile_api.json
# 编辑 data/mobile_api.json 设 api_token，App 里填同一个

uvicorn app.main:app --host 0.0.0.0 --port 8765
```

前面用 **Nginx** 配 HTTPS，或使用 Cloudflare 代理，最终得到例如：

`https://job-guard.你的域名.com`

### 自检（在电脑浏览器或手机浏览器）

打开：`https://你的域名/api/mobile/status`  
应看到 `"ok": true`。

---

## 第二步：在电脑上制作 APK（Android Studio）

### 1. 安装 Android Studio

- 官网：https://developer.android.com/studio  
- 安装时勾选 **Android SDK**、**Android SDK Platform-Tools**

### 2. 打开工程

1. 启动 Android Studio → **Open**  
2. 选文件夹：**`job-scam-guard/mobile/android`**（不是整个 job-scam-guard 根目录）  
3. 等待右下角 **Gradle Sync** 完成（首次会下载依赖，需联网，约 5～15 分钟）

### 3. 连接 Vivo 手机（真机调试，推荐）

1. 手机：**设置 → 系统管理 → 开发者选项 → USB 调试** 打开  
2. USB 线连电脑，手机上点 **允许 USB 调试**  
3. Android Studio 顶部设备列表里应出现你的机型  

### 4. 运行到手机（最快）

1. 点绿色 **Run ▶**  
2. 自动编译并安装「招聘防骗」  
3. 手机上会自动打开 App  

### 5. 只生成 APK 文件（发给别的手机装）

菜单：**Build → Build Bundle(s) / APK(s) → Build APK(s)**  

成功后点通知里的 **locate**，得到：

`mobile/android/app/build/outputs/apk/debug/app-debug.apk`

把 `app-debug.apk` 传到手机安装（需允许「安装未知应用」）。

---

## 第三步：手机首次设置（Vivo X300 Pro）

### 1. 打开 App「招聘防骗」

| 按钮 | 作用 |
|------|------|
| 服务器地址 | 填 `https://你的域名`（不要末尾 `/`） |
| API Key | 若服务器配置了 `mobile_api.json` 的 token，这里填同一个 |
| 1. 授权悬浮窗 | 跳转系统页，**允许显示在其他应用上层** |
| 2. 授权屏幕录制 | 系统弹窗点 **立即开始 / 允许**（夸克同款录屏权限） |
| 3. 启动悬浮球 | 屏幕边缘出现蓝色小圆球「盾」 |

### 2. OriginOS 额外注意

- **设置 → 电池 → 招聘防骗**：选 **不限制后台** 或 **允许后台高耗电**  
- **设置 → 应用 → 招聘防骗 → 权限**：悬浮窗、通知均允许  
- 若球消失：重新点「启动悬浮球」

---

## 第四步：像夸克一样使用

1. 打开 **BOSS直聘 / 微信 / 智联** 等，停在招聘详情页  
2. **点一下** 悬浮球「盾」（不要拖动；拖动是换位置，松手会贴左/右边缘）  
3. 屏幕变暗 → **手指拖矩形** 框住 JD/聊天文字 → 松手  
4. 等待「截图识别中…」（约 10～30 秒，走云端 OCR）  
5. 顶部弹出 **小卡片结论**（高危/警惕 + 一句话建议），点 ✕ 关闭  
6. 悬浮球仍在，可继续框选别的页面  

与夸克对比：

| 夸克 | 本 App |
|------|--------|
| 小圆悬浮球 | 蓝色「盾」46dp，可贴边 |
| 框选搜题 | 框选招聘文字 |
| 结果浮层 | 顶部结果卡片 |
| 夸克自家云 | **你自己的服务器** |

---

## 工程结构（想改代码时看）

```
mobile/android/
├── app/src/main/java/com/jobscamguard/mobile/
│   ├── MainActivity.kt          # 填服务器、开权限
│   ├── FloatBubbleService.kt    # 小悬浮球
│   ├── CropOverlayActivity.kt   # 全屏框选
│   ├── FloatingResult.kt        # 夸克式结果小窗
│   ├── ScreenCaptureHolder.kt   # 截屏
│   └── ApiClient.kt             # 上传图片到云端
└── 制作APP教程.md               # 本文件
```

改默认服务器：编辑 `MainActivity.kt` 里 `serverUrl` 的 hint，或在 `Prefs` 里写默认值。

改悬浮球大小：改 `res/layout/bubble.xml` 的 `46dp`。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| Gradle 同步失败 | 检查网络；File → Settings → 配置国内 Maven 镜像 |
| 安装后打不开悬浮球 | 先完成「授权悬浮窗」 |
| 点球没反应 | 先「授权屏幕录制」 |
| 401 错误 | API Key 与服务器 `mobile_api.json` 不一致 |
| 识别失败 | 框选更大、更清晰；或换粘贴：浏览器打开 `/mobile` |
| 只有 debug APK | 正式发布需 Build → Generate Signed Bundle/APK |

---

## 不想自己编译？

可以请有 Android Studio 的朋友按 **第二步** 帮你打 `app-debug.apk`；  
你只需完成 **第一步云端** + **第三步手机配置**。

服务器不会部署时，可以说一下你更方便用「云服务器」还是「Tunnel 穿透」，再单独写一版部署步骤。
