@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
    python run_desktop.py
) else (
    py -3 run_desktop.py
)
if errorlevel 1 pause
