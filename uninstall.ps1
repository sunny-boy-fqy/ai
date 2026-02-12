# AI Tool Deep Uninstallation Script for Windows

# 1. Self-cloning logic: Move to Temp to avoid "Folder in use" error
$CurrentPath = $PSCommandPath
if ($CurrentPath -notlike "$env:TEMP*") {
    $tempDir = Join-Path $env:TEMP "ai_uninstall_$(Get-Date -Format 'yyyyMMddHHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    $tempScript = Join-Path $tempDir "uninstall.ps1"
    Copy-Item $CurrentPath $tempScript -Force
    
    Write-Host "⏳ Preparing deep cleanup environment..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$tempScript`""
    exit
}

Write-Host "=== 🗑️ AI CLI Deep Uninstallation ===" -ForegroundColor Cyan

# 2. Kill all related processes
Write-Host "🛑 Stopping AI processes and plugins..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.CommandLine -like "*ai_caller.py*" -or $_.Name -eq "ai" } | Stop-Process -Force -ErrorAction SilentlyContinue
# Kill node processes running from our config dir
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*\.config\ai\node\*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. Identify paths
$CONFIG_DIR = "$HOME\.config\ai"
$BASE_PATH_FILE = "$CONFIG_DIR\base_path.config"
if (Test-Path "$BASE_PATH_FILE") {
    $TARGET_DIR = Get-Content "$BASE_PATH_FILE" -Raw -Encoding utf8 | Select-Object -First 1
} else {
    $TARGET_DIR = "$HOME\ai"
}

# 4. Delete everything
Write-Host "📁 Deleting configuration and environments..." -ForegroundColor Yellow
if (Test-Path "$CONFIG_DIR") { Remove-Item -Path "$CONFIG_DIR" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "$HOME\.ai") { Remove-Item -Path "$HOME\.ai" -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host "📁 Deleting source code at $TARGET_DIR ..." -ForegroundColor Yellow
if (Test-Path "$TARGET_DIR") { 
    Remove-Item -Path "$TARGET_DIR" -Recurse -Force -ErrorAction SilentlyContinue 
}

# 5. PATH Cleanup
Write-Host "🔗 Cleaning User PATH..." -ForegroundColor Yellow
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -like "*$TARGET_DIR*") {
    $PathList = $UserPath.Split(';') | Where-Object { $_ -ne $TARGET_DIR -and $_ -ne "$TARGET_DIR\" -and $_ -ne "" }
    $NewPath = $PathList -join ';'
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
}

Write-Host "`n✅ Uninstallation Complete! All files and processes cleared." -ForegroundColor Green
Write-Host "You can now close this window."
pause
