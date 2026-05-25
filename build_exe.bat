@echo off
REM ============================================================
REM  STN READER Viewer - Windows .exe builder
REM  Run from the project root in Command Prompt:
REM      build_exe.bat
REM ============================================================

setlocal enabledelayedexpansion

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not on PATH. Install Python 3.11+ from
    echo         https://www.python.org/downloads/  and re-run this script.
    exit /b 1
)

if not exist .venv (
    echo [1/4] Creating virtual environment ^(.venv^)...
    python -m venv .venv
    if errorlevel 1 exit /b 1
) else (
    echo [1/4] Reusing existing .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip >nul

echo [3/4] Installing runtime + build dependencies...
pip install -r requirements-viewer.txt
if errorlevel 1 exit /b 1
pip install "pyinstaller>=6.0"
if errorlevel 1 exit /b 1

echo [4/4] Running PyInstaller...
pyinstaller --clean --noconfirm viewer.spec
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  BUILD FAILED  - scroll up to see PyInstaller errors.
    echo ============================================================
    exit /b 1
)

set "EXE=dist\STN-Reader\STN-Reader.exe"
if exist "%EXE%" (
    echo.
    echo ============================================================
    echo  BUILD SUCCEEDED
    echo  Exe location: %EXE%
    echo.
    echo  Double-click the .exe inside dist\STN-Reader\
    echo  to launch the viewer. Distribute the whole folder
    echo  ^(or zip it^) - the .exe needs the sibling DLLs.
    echo ============================================================
) else (
    echo [ERROR] PyInstaller finished but %EXE% is missing.
    exit /b 1
)

endlocal
