@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title 招聘防骗-ngrok

echo ========================================
echo   ngrok 隧道（Cloudflare 卡住时用，推荐）
echo ========================================
echo.
echo 第一次使用:
echo   1. 打开 https://dashboard.ngrok.com/signup 注册
echo   2. 下载 Windows 版 ngrok，解压 ngrok.exe 到:
echo      %~dp0
echo   3. 在网站复制 authtoken，在本窗口执行:
echo      ngrok config add-authtoken 粘贴token
echo.

if not exist "%~dp0ngrok.exe" (
  where ngrok >nul 2>&1
  if errorlevel 1 (
    echo [错误] 找不到 ngrok.exe
    echo 请放到: %~dp0ngrok.exe
    pause
    exit /b 1
  )
  set NGROK=ngrok
) else (
  set NGROK=%~dp0ngrok.exe
)

if not exist ".venv\Scripts\python.exe" (
  echo 请先运行 首次安装依赖.bat
  pause
  exit /b 1
)

curl -s -o nul http://127.0.0.1:8765/api/mobile/status 2>nul
if errorlevel 1 (
  echo 启动 API...
  start "招聘防骗-API" /D "%CD%" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765"
  timeout /t 5 /nobreak >nul
)

echo.
echo ========================================
echo 下面会出现 Forwarding 一行，例如:
echo   https://abcd-1234.ngrok-free.app
echo 手机 App 填这个 https 地址（不要带 /api/...）
echo.
echo 也可打开浏览器 http://127.0.0.1:4040 查看网址
echo 不要关本窗口！
echo ========================================
echo.

"%NGROK%" http 8765

pause
