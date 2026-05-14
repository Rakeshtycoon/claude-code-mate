# Flutter Windows Installation Script
# Source: C:\Users\rcmak\Downloads\flutter_windows_3.41.9-stable

param(
    [string]$SourcePath = "C:\Users\rcmak\Downloads\flutter_windows_3.41.9-stable",
    [string]$InstallPath = "C:\flutter"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Flutter 3.41.9 Windows Installation  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check source path
Write-Host "[1/5] Source folder check kari raha hai..." -ForegroundColor Yellow
if (-Not (Test-Path $SourcePath)) {
    Write-Host "ERROR: Source folder maldo nathi: $SourcePath" -ForegroundColor Red
    Write-Host "Please check karo ke Flutter folder aa path par chhe." -ForegroundColor Red
    exit 1
}
Write-Host "  Source folder malyun: $SourcePath" -ForegroundColor Green

# Step 2: Copy Flutter to install location
Write-Host ""
Write-Host "[2/5] Flutter ne $InstallPath ma copy kari raha hai..." -ForegroundColor Yellow

if (Test-Path $InstallPath) {
    Write-Host "  WARNING: $InstallPath pehela thi exist kare chhe. Overwrite thase." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallPath
}

Copy-Item -Recurse -Force $SourcePath $InstallPath
Write-Host "  Flutter copy thayun: $InstallPath" -ForegroundColor Green

# Step 3: Add Flutter to PATH (User level)
Write-Host ""
Write-Host "[3/5] Flutter ne PATH ma add kari raha hai..." -ForegroundColor Yellow

$flutterBin = "$InstallPath\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($currentPath -notlike "*$flutterBin*") {
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$currentPath;$flutterBin",
        "User"
    )
    Write-Host "  Flutter PATH ma add thayun: $flutterBin" -ForegroundColor Green
} else {
    Write-Host "  Flutter pehela thi PATH ma chhe." -ForegroundColor Green
}

# Refresh PATH in current session
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")

# Step 4: Verify flutter binary exists
Write-Host ""
Write-Host "[4/5] Flutter binary verify kari raha hai..." -ForegroundColor Yellow

$flutterExe = "$flutterBin\flutter.bat"
if (Test-Path $flutterExe) {
    Write-Host "  flutter.bat malyun!" -ForegroundColor Green
} else {
    Write-Host "ERROR: flutter.bat nathi malyu at $flutterExe" -ForegroundColor Red
    Write-Host "Please check karo ke source folder correct chhe." -ForegroundColor Red
    exit 1
}

# Step 5: Run flutter doctor
Write-Host ""
Write-Host "[5/5] Flutter doctor chalavi raha hai..." -ForegroundColor Yellow
Write-Host "  (Aa thodi vaar le shake chhe...)" -ForegroundColor Gray
Write-Host ""

try {
    & "$flutterExe" doctor
} catch {
    Write-Host "flutter doctor chalavi nai shakyo. Manually chalavo:" -ForegroundColor Yellow
    Write-Host "  flutter doctor" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Puri Thayi!              " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Hu notes:" -ForegroundColor White
Write-Host "  1. Navi terminal/PowerShell kholo jethI PATH update thay" -ForegroundColor White
Write-Host "  2. 'flutter doctor' command chalavo baaki setup jova" -ForegroundColor White
Write-Host "  3. Android Studio install hoy to Android targets malse" -ForegroundColor White
Write-Host ""
Write-Host "Flutter version check karva: flutter --version" -ForegroundColor Cyan
