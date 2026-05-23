@echo off
cd /d "%~dp0frontend"
echo Building frontend...
call npx vite build >nul 2>&1
echo Starting server...
cd /d "%~dp0backend"
python main.py
pause
