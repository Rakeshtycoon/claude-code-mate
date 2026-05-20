@echo off
REM ===================================================================
REM  Build adv-analyzer.exe on Windows.
REM  Run this from the adv-scanner project root:  packaging\build_windows.bat
REM ===================================================================
setlocal
cd /d "%~dp0\.."
echo === adv-analyzer Windows build ===
echo project root: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python not found on PATH. Install Python 3.10+ first.
    exit /b 1
)

echo [1/3] installing build dependencies...
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r packaging\requirements-build.txt || exit /b 1
echo.

echo [2/3] cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo [3/3] running PyInstaller...
python -m PyInstaller --clean --noconfirm packaging\adv-analyzer.spec || exit /b 1
echo.

echo === BUILD COMPLETE ===
echo Executable:  dist\adv-analyzer.exe
echo.
echo Quick test:
echo     dist\adv-analyzer.exe --help
echo     dist\adv-analyzer.exe extract path\to\scan.adv -o output_folder
endlocal
