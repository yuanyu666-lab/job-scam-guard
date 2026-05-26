@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title 招聘防骗-隧道

echo ========================================
echo   公网隧道 (HTTP/2)
echo ========================================
echo.

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 cloudflared
  pause
  exit /b 1
)

curl -s -o nul http://127.0.0.1:8765/api/mobile/status 2>nul
if errorlevel 1 (
  echo [警告] 8765 端口没有 API！请先保持「招聘防骗-API」窗口运行。
  echo.
)

echo 预检查通过后，可能还要等 30~90 秒才会出现网址。
echo 请盯着下面是否出现:  https://xxxx.trycloudflare.com
echo.
echo 若超过 2 分钟仍只有 precheck complete 且无 https:
echo   按 Ctrl+C 结束，改双击 scripts\手机公网隧道-ngrok.bat
echo.

set CF_TUNNEL_TRANSPORT_PROTOCOL=http2
cloudflared tunnel --protocol http2 --url http://127.0.0.1:8765 --loglevel info

echo.
echo 隧道已结束
pause
