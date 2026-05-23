@echo off
REM ============================================================
REM  ADV Planning Data Recovery - one-time setup (Windows)
REM
REM  Double-click this file ONCE after downloading the project.
REM  It installs all Python dependencies that the tool needs.
REM ============================================================

setlocal
cd /d "%~dp0\.."

echo.
echo === Checking Python ===
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo  1. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo  2. During install, TICK the "Add Python to PATH" checkbox
    echo  3. Then run this file again.
    pause
    exit /b 1
)

echo.
echo === Installing dependencies (this can take 5-10 minutes) ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo === Done ===
echo You can now:
echo   - double-click  2-open-viewer.bat       to open the 3D viewer
echo   - double-click  3-convert-file.bat      to convert one .adv to OBJ/STL
echo   - double-click  4-convert-folder.bat    to batch-convert many files
echo   - double-click  5-show-file-info.bat    to inspect a .adv file
echo.
pause
