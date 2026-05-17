# Diamond Converter - Windows Build Guide
# Project Path: F:\CONVERTOR PROJECT\diamond_converter

## Step 1: Required Software Install

### 1. Qt 6.x (with Qt Creator)
- Download: https://www.qt.io/download-open-source
- Install with: Qt 6.x → MSVC 2019/2022 64-bit OR MinGW 64-bit

### 2. CMake
- Download: https://cmake.org/download/
- Version 3.16 or newer

### 3. 7-Zip
- Download: https://www.7-zip.org/
- Install to default path: C:\Program Files\7-Zip\

### 4. Visual Studio 2019/2022 (Community - Free)
- OR: MinGW (comes with Qt)

---

## Step 2: Build karo

### Qt Creator thi (Easiest way):
1. Qt Creator open karo
2. File → Open File or Project
3. `F:\CONVERTOR PROJECT\diamond_converter\CMakeLists.txt` select karo
4. Configure → Build

### Command Line thi:
```cmd
cd "F:\CONVERTOR PROJECT\diamond_converter"
mkdir build
cd build

:: Qt path tari install location mukabi change karo
cmake .. -DCMAKE_PREFIX_PATH="C:\Qt\6.x.x\msvc2019_64"

cmake --build . --config Release
```

---

## Step 3: Qt DLLs copy karo (exe run karvaa)

```cmd
cd "F:\CONVERTOR PROJECT\diamond_converter\build\Release"
windeployqt DiamondConverter.exe
```

---

## Step 4: Run
```cmd
"F:\CONVERTOR PROJECT\diamond_converter\build\Release\DiamondConverter.exe"
```

---

## Troubleshooting

### "7-zip not found"
- Check: `C:\Program Files\7-Zip\7z.exe` exist kare chhe?
- Jо nahи: 7-zip install karo: https://www.7-zip.org/

### "Qt6 not found"
- CMake command ma `-DCMAKE_PREFIX_PATH` tari Qt install path mukab change karo
- Example: `C:\Qt\6.7.0\msvc2022_64`

### OpenGL error
- Graphics drivers update karo
- Intel/NVIDIA/AMD latest driver install karo
