@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set SRC=data
set DST=data-for-github

if not exist "%SRC%\patterns.json" (
  echo [错误] 找不到 %SRC%\patterns.json
  pause
  exit /b 1
)

if not exist "%DST%" mkdir "%DST%"

copy /Y "%SRC%\patterns.json" "%DST%\" >nul
copy /Y "%SRC%\ocr_config.json" "%DST%\" >nul 2>nul
copy /Y "%SRC%\*.example" "%DST%\" >nul

echo 已同步到 %DST%\
echo 可上传 %DST% 文件夹内全部文件到 GitHub 的 data/ 目录
dir /B "%DST%"
echo.
pause
