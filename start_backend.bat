@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title myapp local backend
cd /d "%~dp0local-backend"

echo ============================================================
echo  Mapping phone port 8080 to this PC (USB required)
echo ============================================================
adb reverse tcp:8080 tcp:8080
if errorlevel 1 (
    echo.
    echo [WARN] adb reverse failed.
    echo        Connect the phone, enable USB debugging, and make sure adb is in PATH.
    echo.
)

echo.
echo  Starting local backend. Keep this window open...
echo.
python server.py

echo.
echo Local backend stopped.
pause
