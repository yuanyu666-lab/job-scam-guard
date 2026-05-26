@echo off
chcp 65001 >nul
title 上传 job-scam-guard 到 GitHub
cd /d "%~dp0"

set GIT=D:\Git\cmd\git.exe
set GH=C:\Program Files\GitHub CLI\gh.exe

echo ========================================
echo   招聘防骗系统 - 上传到 GitHub
echo ========================================
echo.

if not exist "%GIT%" (
    echo [错误] 未找到 Git: D:\Git\cmd\git.exe
    pause
    exit /b 1
)

echo [1/4] 检查本地仓库...
"%GIT%" status
echo.

if not exist ".git" (
    echo [2/4] 初始化仓库...
    "%GIT%" init
    "%GIT%" branch -M main
    "%GIT%" add .
    "%GIT%" commit -m "Initial commit: job scam guard MVP"
) else (
    echo [2/4] 本地仓库已存在，跳过初始化
)

echo.
echo [3/4] 登录 GitHub（会打开浏览器，按提示点授权即可）...
"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    "%GH%" auth login -h github.com -p https -w --skip-ssh-key
)

echo.
echo [4/4] 创建仓库并上传...
"%GH%" repo create job-scam-guard --public --source=. --remote=origin --push --description "招聘防骗系统 MVP"

if errorlevel 1 (
    echo.
    echo 若提示仓库已存在，尝试直接推送...
    "%GIT%" remote add origin https://github.com/yuanyu/job-scam-guard.git 2>nul
    "%GIT%" push -u origin main
)

echo.
echo ========================================
"%GH%" repo view --json url -q .url 2>nul
echo 完成！若上方有链接，即上传成功。
echo ========================================
pause
