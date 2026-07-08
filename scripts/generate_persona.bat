@echo off
cd /d "%~dp0.."
echo ========================================
echo  SOSchatroom - Persona Generator
echo ========================================
echo.
echo  Generates character personas from graph + novel text.
echo  Existing files are NOT overwritten - numbered copies are created.
echo  Example: haruhi.txt -> haruhi_1.txt -> haruhi_2.txt
echo.
echo ========================================
echo.

python backend/scripts/generate_persona.py --numbered

echo.
echo Done. Check backend/personas/ for output files.
echo ========================================
pause
