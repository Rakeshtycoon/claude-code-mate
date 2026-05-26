@echo off
REM ============================================================
REM  STN READER Viewer - Windows .exe builder
REM
REM  RUN FROM A COMMAND PROMPT, e.g.:
REM      cd /d "F:\CONVERTOR PROJECT\stn-reader"
REM      build_exe.bat
REM
REM  (Double-clicking from Explorer also works because the script
REM  pauses at the end so the window stays open.)
REM ============================================================

setlocal

REM --- Pick the best available Python --------------------------
set "PY_CMD="

call :try_pick_python 3.12
if not defined PY_CMD call :try_pick_python 3.11
if not defined PY_CMD call :try_pick_python 3.10
if not defined PY_CMD call :try_pick_python 3.9

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
    echo.
    echo [ERROR] No Python found.
    echo         Install Python 3.11 from
    echo            https://www.python.org/downloads/release/python-3119/
    echo         then re-run this script.
    goto :end
)

REM --- Virtual environment -------------------------------------
if not exist .venv (
    echo [1/4] Creating virtual environment ^(.venv^) with %PY_CMD%...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create .venv with %PY_CMD%.
        goto :end
    )
) else (
    echo [1/4] Reusing existing .venv
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Could not activate .venv\Scripts\activate.bat
    goto :end
)

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    goto :end
)

echo [3/4] Installing runtime + build dependencies...
pip install -r requirements-viewer.txt
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  DEPENDENCY INSTALL FAILED
    echo.
    echo  Most common cause: Python version not supported by PySide6
    echo  / PyVista yet. Install Python 3.11 from
    echo     https://www.python.org/downloads/release/python-3119/
    echo  delete the .venv folder, and re-run this script.
    echo ============================================================
    goto :end
)
pip install "pyinstaller>=6.0"
if errorlevel 1 (
    echo [ERROR] PyInstaller install failed.
    goto :end
)

echo [4/4] Running PyInstaller...
pyinstaller --clean --noconfirm viewer.spec
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  BUILD FAILED  - scroll up to see PyInstaller errors.
    echo ============================================================
    goto :end
)

set "EXE=dist\STN-Reader\STN-Reader.exe"
if exist "%EXE%" (
    echo.
    echo ============================================================
    echo  BUILD SUCCEEDED
    echo  Exe location: %EXE%
    echo.
    echo  Double-click the .exe inside dist\STN-Reader\ to launch.
    echo  Distribute the WHOLE folder ^(or zip it^).
    echo ============================================================
) else (
    echo [ERROR] PyInstaller finished but %EXE% is missing.
)

:end
echo.
echo Press any key to close this window.
pause >nul
endlocal
exit /b

REM ============================================================
REM  Helper: try one Python version via the py launcher
REM ============================================================
:try_pick_python
    py -%~1 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -%~1"
        echo [info] Using Python %~1 via py launcher
    )
    goto :eof
