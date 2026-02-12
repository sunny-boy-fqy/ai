# AI Tool Uninstallation Script for Windows

Write-Host "=== 🗑️  AI CLI Uninstallation (Windows) ===" -ForegroundColor Cyan

$CONFIG_DIR = "$HOME\.config\ai"
$BASE_PATH_FILE = "$CONFIG_DIR\base_path.config"

if (Test-Path $BASE_PATH_FILE) {
    $TARGET_DIR = Get-Content $BASE_PATH_FILE -Raw
} else {
    $TARGET_DIR = "$HOME\.ai"
}

# 1. Remove from PATH
Write-Host "Removing $TARGET_DIR from User PATH..."
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -like "*$TARGET_DIR*") {
    $NewPath = ($CurrentPath.Split(';') | Where-Object { $_ -ne $TARGET_DIR }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "✅ Removed $TARGET_DIR from User PATH." -ForegroundColor Green
} else {
    Write-Host "ℹ️ $TARGET_DIR not found in User PATH." -ForegroundColor Yellow
}

# 2. Delete Directories
Write-Host "Deleting configuration directory $CONFIG_DIR ..." -ForegroundColor Cyan
if (Test-Path "$CONFIG_DIR") {
    Remove-Item -Path "$CONFIG_DIR" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Deleted config dir." -ForegroundColor Green
}

Write-Host "Deleting tool directory contents at $TARGET_DIR ..." -ForegroundColor Cyan
if (Test-Path "$TARGET_DIR") {
    # We cannot delete the folder itself because the script is running inside it.
    # We will delete everything EXCEPT the script itself and the .sh version.
    $currentScript = $MyInvocation.MyCommand.Path
    Get-ChildItem -Path "$TARGET_DIR" | Where-Object { $_.FullName -ne $currentScript -and $_.Name -ne "uninstall.sh" } | ForEach-Object {
        try {
            Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        } catch {}
    }
    Write-Host "✅ Cleaned most of the tool directory." -ForegroundColor Green
    Write-Host "ℹ️ Please manually delete the folder '$TARGET_DIR' after closing this terminal." -ForegroundColor Yellow
}

Write-Host "`n✅ Uninstallation tasks completed!" -ForegroundColor Green
