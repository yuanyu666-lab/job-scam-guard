@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title 招聘防骗-启动器

echo ========================================
echo   招聘防骗 - 手机公网隧道（无需买服务器）
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 未找到虚拟环境，正在运行首次安装依赖...
  call "%~dp0..\首次安装依赖.bat"
  if not exist ".venv\Scripts\python.exe" (
    echo 安装失败：请先安装 Python 3.10+ 再重试。
    pause
    exit /b 1
  )
)

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 cloudflared 隧道工具。
  echo.
  echo 请用管理员打开 PowerShell 执行：
  echo   winget install Cloudflare.cloudflared
  echo.
  echo 安装后重启电脑，再双击本脚本。
  pause
  exit /b 1
)

echo [2/3] 启动本地 API（窗口「招聘防骗-API」）...
start "招聘防骗-API" /D "%~dp0.." cmd /k ""%~dp0..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

echo 等待 API 就绪...
timeout /t 4 /nobreak >nul

curl -s -o nul http://127.0.0.1:8765/api/mobile/status 2>nul
if errorlevel 1 (
  echo [警告] API 可能未就绪，请等 API 窗口出现 Uvicorn running 后再看隧道窗口
)

echo [3/3] 启动公网隧道...
echo.
echo 预检查通过后请再等 30~90 秒找 https://....trycloudflare.com
echo 若 2 分钟仍无网址 / 一直不动: 关掉隧道窗，改运行 scripts\手机公网隧道-ngrok.bat
echo.
echo 两个窗口都不要关！关掉后手机无法连接。
echo.

start "招聘防骗-隧道" cmd /k "%~dp0手机公网隧道-仅隧道.cmd"

echo.
echo 已启动。若隧道窗口没有地址，等 10 秒查看。
pause
