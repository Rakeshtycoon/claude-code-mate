@echo off
REM ============================================================
REM  STN READER Viewer - Windows .exe builder
REM  Run from the project root in Command Prompt:
REM      build_exe.bat
REM
REM  Prefers Python 3.11 / 3.12 (best compatibility with PySide6
REM  and PyVista). Falls back to whatever `python` is on PATH.
REM ============================================================

setlocal enabledelayedexpansion

REM --- Pick the best available Python --------------------------
set "PY_CMD="

for %%V in (3.12 3.11 3.10 3.9) do (
    if not defined PY_CMD (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=py -%%V"
            echo [info] Using Python %%V via py launcher
        )
    )
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        echo [info] Using default 'python' on PATH
        echo [warn] Recommended versions are 3.11 or 3.12 - PySide6 / PyVista
        echo [warn] may not yet support newer Python. If the build fails,
        echo [warn] install Python 3.11 from
        echo [warn]   https://www.python.org/downloads/release/python-3119/
    )
)

if not defined PY_CMD (
    echo [ERROR] No Python found on PATH and the 'py' launcher does not know
    echo         about any 3.9 / 3.10 / 3.11 / 3.12 installation.
    echo         Install Python 3.11 from
    echo            https://www.python.org/downloads/release/python-3119/
    echo         then re-run this script.
    exit /b 1
)

REM --- Virtual environment -------------------------------------
if not exist .venv (
    echo [1/4] Creating virtual environment ^(.venv^)...
    %PY_CMD% -m venv .venv
    if errorlevel 1 exit /b 1
) else (
    echo [1/4] Reusing existing .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip >nul

echo [3/4] Installing runtime + build dependencies...
pip install -r requirements-viewer.txt
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  DEPENDENCY INSTALL FAILED
    echo  Most common cause: Python version not supported by PySide6
    echo  / PyVista yet. Install Python 3.11 from
    echo    https://www.python.org/downloads/release/python-3119/
    echo  delete the .venv folder, and re-run this script.
    echo ============================================================
    exit /b 1
)
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
