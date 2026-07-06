@echo off
chcp 65001 >nul
cd /d "%~dp0..\backend"

:: Kill old process on port 8001 if any
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo [GraphRAG] Starting server...
start http://localhost:8001
python server_graphrag.py
pause
