@echo off
REM ============================================================
REM  Show what is inside a .adv file (structure, metadata,
REM  planning tree, number of saw planes / planned stones).
REM  Nothing is written; this just prints information.
REM ============================================================

setlocal
cd /d "%~dp0\.."

echo.
echo Drag-and-drop your .adv file, then press Enter:
set /p ADVFILE=^>
set ADVFILE=%ADVFILE:"=%
if "%ADVFILE%"=="" goto :empty

python -m advrecover info "%ADVFILE%"
echo.
python -m advrecover planning "%ADVFILE%" --list

echo.
pause
goto :eof

:empty
echo No file given. Closing.
pause
