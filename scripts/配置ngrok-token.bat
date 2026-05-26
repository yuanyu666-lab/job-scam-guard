@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 配置 ngrok token

echo ========================================
echo   ngrok authtoken 配置助手
echo ========================================
echo.
echo 【token 在哪找】
echo   1. 浏览器打开: https://dashboard.ngrok.com/get-started/your-authtoken
echo   2. 登录 ngrok 账号（没有就先注册）
echo   3. 页面上会有一串类似 2abc...xyz 的 Authtoken，点 Copy 复制
echo.

if not exist "%~dp0ngrok.exe" (
  where ngrok >nul 2>&1
  if errorlevel 1 (
    echo [错误] 未找到 ngrok.exe
    echo 请先下载: https://ngrok.com/download
    echo 解压 ngrok.exe 到本文件夹: %~dp0
    echo.
    pause
    exit /b 1
  )
  set NGROK=ngrok
) else (
  set NGROK=%~dp0ngrok.exe
)

echo 【在本窗口粘贴 token】
echo 复制 token 后，在下面输入（粘贴后按回车）:
echo.
set /p TOKEN=Authtoken: 

if "%TOKEN%"=="" (
  echo 未输入 token，已取消
  pause
  exit /b 1
)

echo.
echo 正在配置...
"%NGROK%" config add-authtoken %TOKEN%
if errorlevel 1 (
  echo 配置失败，请检查 token 是否完整
) else (
  echo.
  echo [成功] 配置完成！现在可以双击: 手机公网隧道-ngrok.bat
)
echo.
pause
