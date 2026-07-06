@echo off
echo === SOS Brigade Chatroom ===
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Install frontend deps if missing
if not exist "%~dp0..\frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%~dp0..\frontend"
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend dependency installation failed
        pause
        exit /b 1
    )
    cd /d "%~dp0"
)

REM Build frontend
echo [1/2] Building frontend...
cd /d "%~dp0..\frontend"
call npx vite build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)

REM Start backend
echo [2/2] Starting server...
cd /d "%~dp0..\backend"
python main.py

pause
