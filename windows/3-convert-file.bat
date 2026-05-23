@echo off
REM ============================================================
REM  Convert ONE .adv file to OBJ / STL
REM
REM  When asked, DRAG-AND-DROP your .adv file into this window,
REM  then press Enter. The output appears in windows\output\
REM ============================================================

setlocal
cd /d "%~dp0\.."

echo.
echo Drag-and-drop your .adv file into this window, then press Enter:
set /p ADVFILE=^>
set ADVFILE=%ADVFILE:"=%
if "%ADVFILE%"=="" goto :empty

echo.
echo Available planning solutions in this file:
python -m advrecover planning "%ADVFILE%" --list

echo.
echo Type a solution number to render JUST that one (or press Enter for ALL):
set /p SOL=^>

if "%SOL%"=="" (
    python -m advrecover planning "%ADVFILE%" --out "%~dp0output" --format both
) else (
    python -m advrecover planning "%ADVFILE%" --solution %SOL% --out "%~dp0output" --format both
)

echo.
echo === Done ===
echo Files saved in: %~dp0output
echo Open the .obj file with the Windows 3D Viewer app, or upload to https://3dviewer.net
echo.
pause
goto :eof

:empty
echo No file given. Closing.
pause
