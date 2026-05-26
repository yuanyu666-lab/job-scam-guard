@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\self_check.py
exit /b %ERRORLEVEL%
