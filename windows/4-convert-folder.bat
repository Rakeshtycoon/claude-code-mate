@echo off
REM ============================================================
REM  Convert EVERY .adv file in a folder, all at once
REM
REM  Drag-and-drop the folder containing .adv files when asked.
REM  All OBJ + STL outputs go into windows\output_batch\
REM ============================================================

setlocal
cd /d "%~dp0\.."

echo.
echo Drag-and-drop the FOLDER containing .adv files, then press Enter:
set /p ADVFOLDER=^>
set ADVFOLDER=%ADVFOLDER:"=%
if "%ADVFOLDER%"=="" goto :empty

python -m advrecover batch "%ADVFOLDER%" --out "%~dp0output_batch" --format both

echo.
echo === Done ===
echo Files saved in: %~dp0output_batch
echo.
pause
goto :eof

:empty
echo No folder given. Closing.
pause
