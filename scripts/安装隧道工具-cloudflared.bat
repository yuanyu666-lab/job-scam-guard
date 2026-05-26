@echo off
chcp 65001 >nul
echo 正在安装 Cloudflare 隧道（winget）...
echo 若失败，请用管理员身份运行本脚本。
echo.
winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
echo.
echo 安装后请重启电脑，再运行「手机公网隧道.bat」
pause
