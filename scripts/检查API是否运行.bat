@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title 检查 API

echo 检查本机 8765 端口是否在跑...
curl -s -o nul -w "HTTP状态: %%{http_code}\n" http://127.0.0.1:8765/api/mobile/status 2>nul
if errorlevel 1 (
  echo.
  echo [失败] API 没起来。请先双击 scripts\手机公网隧道.bat
  echo 或手动开窗口运行:
  echo   .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
) else (
  echo.
  echo [OK] API 正常，可以再开隧道窗口
)
echo.
pause
