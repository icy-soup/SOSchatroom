@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
echo [GraphRAG] Server on port 8001 stopped.
pause
