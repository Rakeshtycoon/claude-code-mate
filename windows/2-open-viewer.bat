@echo off
REM ============================================================
REM  Open the 3D viewer (PySide6 + PyVista desktop app)
REM
REM  In the viewer:
REM    File -> Open .ADV          to load a file
REM    Solutions tab (left)        to pick a planning solution
REM    Previews tab (left)         to see the ORIGINAL Advisor renders
REM                                (double-click any thumbnail to enlarge)
REM    Layers (right)              to toggle rough/planes/stones
REM    File -> Export OBJ / STL    to save the 3D model
REM    File -> Export all previews to save every embedded JPEG
REM ============================================================

setlocal
cd /d "%~dp0\.."
python -m advrecover gui
if errorlevel 1 (
    echo.
    echo The viewer exited with an error.
    echo If it failed to open, your computer probably needs an
    echo OpenGL driver update or a different Python install.
    echo You can still use 3-convert-file.bat without the viewer.
)
pause
