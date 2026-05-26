@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating venv, run "??????.bat" first if this fails.
  python -m venv .venv
)
echo Starting...
".venv\Scripts\python.exe" float_app.py
if errorlevel 1 pause