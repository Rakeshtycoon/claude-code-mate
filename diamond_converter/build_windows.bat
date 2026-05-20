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
set MINGW_PATH=
for %%v in (6.11.1 6.11.0 6.10.0 6.9.0 6.8.0 6.7.0 6.6.0 6.5.0 6.4.2 6.3.0) do (
    if exist "C:\Qt\%%v\msvc2022_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\msvc2022_64
        set USE_MINGW=0
        goto found_qt
    )
    if exist "C:\Qt\%%v\msvc2019_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\msvc2019_64
        set USE_MINGW=0
        goto found_qt
    )
    if exist "C:\Qt\%%v\mingw_64\lib\cmake\Qt6" (
        set QT_PATH=C:\Qt\%%v\mingw_64
        set USE_MINGW=1
        goto found_qt
    )
)

echo [ERROR] Qt6 not found. Please edit this script and set QT_PATH manually.
echo Example: set QT_PATH=C:\Qt\6.11.1\mingw_64
pause
exit /b 1

:found_qt
echo [OK] Qt6 found at: %QT_PATH%

:: Find MinGW if needed
if "%USE_MINGW%"=="1" (
    set MINGW_PATH=
    for %%v in (14.2.0 13.1.0 12.0.0 11.2.0) do (
        if exist "C:\Qt\Tools\mingw%%v_64\bin\gcc.exe" (
            set MINGW_PATH=C:\Qt\Tools\mingw%%v_64
            goto found_mingw
        )
    )
    :: Try direct search
    for /d %%d in ("C:\Qt\Tools\mingw*_64") do (
        if exist "%%d\bin\gcc.exe" (
            set MINGW_PATH=%%d
            goto found_mingw
        )
    )
    echo [WARNING] MinGW not found in C:\Qt\Tools - CMake may fail
    goto found_mingw
    :found_mingw
    if not "%MINGW_PATH%"=="" (
        echo [OK] MinGW found at: %MINGW_PATH%
        set PATH=%MINGW_PATH%\bin;%PATH%
    )
)

:: Create build directory
if not exist "build" mkdir build
cd build

:: Configure
echo.
echo [BUILD] Configuring with CMake...
if "%USE_MINGW%"=="1" (
    cmake .. -G "MinGW Makefiles" -DCMAKE_PREFIX_PATH="%QT_PATH%" -DCMAKE_BUILD_TYPE=Release
) else (
    cmake .. -DCMAKE_PREFIX_PATH="%QT_PATH%" -DCMAKE_BUILD_TYPE=Release
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed!
    pause
    exit /b 1
)

:: Build
echo.
echo [BUILD] Building...
if "%USE_MINGW%"=="1" (
    cmake --build . --parallel
) else (
    cmake --build . --config Release --parallel
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

:: Deploy Qt DLLs
echo.
echo [DEPLOY] Copying Qt DLLs...
if "%USE_MINGW%"=="1" (
    "%QT_PATH%\bin\windeployqt.exe" DiamondConverter.exe --no-translations
) else (
    cd Release
    "%QT_PATH%\bin\windeployqt.exe" DiamondConverter.exe --no-translations
    cd ..
)

echo.
echo ============================================
echo   BUILD SUCCESSFUL!
if "%USE_MINGW%"=="1" (
    echo   Executable: build\DiamondConverter.exe
) else (
    echo   Executable: build\Release\DiamondConverter.exe
)
echo ============================================
echo.
pause
