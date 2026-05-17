@echo off
:: Diamond Converter - Windows Build Script
:: Project path: F:\CONVERTOR PROJECT\diamond_converter
:: Run this .bat file from project root

echo ============================================
echo   Diamond Converter - Windows Build Script
echo ============================================
echo.

:: Check 7-zip
if not exist "C:\Program Files\7-Zip\7z.exe" (
    echo [ERROR] 7-Zip not found at C:\Program Files\7-Zip\7z.exe
    echo Please install 7-Zip from https://www.7-zip.org/
    pause
    exit /b 1
)
echo [OK] 7-Zip found

:: Find Qt - common install locations
set QT_PATH=
for %%v in (6.7.0 6.6.0 6.5.0 6.4.2 6.3.0) do (
    if exist "C:\Qt\%%v\msvc2022_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\msvc2022_64
        goto found_qt
    )
    if exist "C:\Qt\%%v\msvc2019_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\msvc2019_64
        goto found_qt
    )
    if exist "C:\Qt\%%v\mingw_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\mingw_64
        goto found_qt
    )
)

echo [ERROR] Qt6 not found. Please edit this script and set QT_PATH manually.
echo Example: set QT_PATH=C:\Qt\6.7.0\msvc2022_64
pause
exit /b 1

:found_qt
echo [OK] Qt6 found at: %QT_PATH%

:: Create build directory
if not exist "build" mkdir build
cd build

:: Configure
echo.
echo [BUILD] Configuring with CMake...
cmake .. -DCMAKE_PREFIX_PATH="%QT_PATH%" -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed!
    pause
    exit /b 1
)

:: Build
echo.
echo [BUILD] Building...
cmake --build . --config Release --parallel
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

:: Deploy Qt DLLs
echo.
echo [DEPLOY] Copying Qt DLLs...
cd Release
"%QT_PATH%\bin\windeployqt.exe" DiamondConverter.exe --no-translations
cd ..

echo.
echo ============================================
echo   BUILD SUCCESSFUL!
echo   Executable: build\Release\DiamondConverter.exe
echo ============================================
echo.
pause
