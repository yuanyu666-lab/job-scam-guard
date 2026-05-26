# GitHub 自动打包 APK（零基础）

不用 Android Studio，在 GitHub 云端编译，下载 `app-debug.apk` 装到 Vivo 手机。

---

## 准备

- GitHub 账号（没有就去 https://github.com/signup 注册）
- 项目文件夹：`D:\Dev\job-scam-guard`
- **不要**把含密钥的文件上传（`data/*_config.json`、`settings.json` 已在 .gitignore）

---

## 方法一：网页上传（最简单，不用装 Git）

### 1. 新建仓库

1. 登录 https://github.com  
2. 右上角 **+** → **New repository**  
3. Repository name 填：`job-scam-guard`（随意）  
4. 选 **Private**（私有，推荐）  
5. **不要**勾选 “Add a README”  
6. 点 **Create repository**

### 2. 上传代码

1. 在新仓库页点 **uploading an existing file**  
2. 把电脑里 **`D:\Dev\job-scam-guard`** 下**所有文件和文件夹**拖进网页  
   - 可以整个拖，体积大时 `.venv` **不要上传**（没有就不用管）  
   - 若网页限制，至少要有：`mobile/android/`、`.github/workflows/`、`app/`、`scripts/` 等  
3. 底部 Commit message 填：`upload project`  
4. 点 **Commit changes**

> 若提示文件太大：不要上传 `.venv` 文件夹；`node_modules` 也没有可忽略。

### 3. 手动触发打包

1. 仓库顶部点 **Actions**  
2. 左侧点 **Build Android APK**  
3. 右侧 **Run workflow** → 分支选 **main**（或 master）→ 绿色 **Run workflow**  
4. 等 **1～10 分钟**，出现绿色 ✓

### 4. 下载 APK

1. 点进这次绿色的运行记录  
2. 页面下方 **Artifacts**  
3. 下载 **app-debug-apk**（是个 zip）  
4. 解压得到 **`app-debug.apk`**  
5. 传到 Vivo 手机安装  

---

## 方法二：用 GitHub Desktop（推荐，以后更新方便）

### 1. 安装

下载：https://desktop.github.com/

### 2. 添加仓库

1. **File → Add local repository**  
2. 选 `D:\Dev\job-scam-guard`  
3. 若提示不是 git 仓库：**create a repository** 创建  

### 3. 首次发布

1. 左下角 Summary 写：`first upload`  
2. 点 **Commit to main**  
3. **Publish repository**（可勾 Private）  

### 4. 打包 APK

同 **方法一 第 3、4 步**：Actions → Build Android APK → Run workflow → 下载 Artifacts  

---

## 方法三：命令行（会 Git 的用户）

```powershell
cd D:\Dev\job-scam-guard
git init
git add .
git commit -m "initial upload"
git branch -M main
git remote add origin https://github.com/你的用户名/job-scam-guard.git
git push -u origin main
```

然后：**Actions → Build Android APK → Run workflow → 下载 APK**

---

## 装到手机后

1. App **服务器地址** 填 ngrok 地址，例如：  
   `https://elaborate-candy-unwieldy.ngrok-free.dev`  
2. 授权悬浮窗 → 授权屏幕录制 → 启动悬浮球  

（电脑 ngrok + API 窗口保持打开）

---

## 打包失败怎么办

1. Actions 里点红色 ✗ 的运行  
2. 点 **build** → 展开红色步骤看报错  
3. 把最后几行错误复制发给我  

常见原因：

| 错误 | 处理 |
|------|------|
| 找不到 `mobile/android` | 上传时漏了 android 文件夹 |
| Gradle 失败 | 把 Actions 日志发我 |
| 没有 Actions 菜单 | 仓库 Settings → Actions → General → 允许运行 |

---

## 说明

- 工作流文件：`.github/workflows/build-android-apk.yml`  
- 每次改完手机代码，在 Actions 里再 **Run workflow** 即可重新打 APK  
- 下载的 APK 30 天内可在 Artifacts 里重复下载  
