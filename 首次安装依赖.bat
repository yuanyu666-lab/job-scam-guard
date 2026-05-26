@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed: install Python 3.10+ first.
    pause
    exit /b 1
  )
)
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
echo Installing requirements, please wait...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Retry with Paddle mirror...
  ".venv\Scripts\python.exe" -m pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
echo.
echo Done. Run "?????.bat" next.
pause