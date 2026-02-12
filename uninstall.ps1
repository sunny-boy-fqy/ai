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
Write-Host "Deleting configuration directory $CONFIG_DIR ..."
if (Test-Path $CONFIG_DIR) {
    Remove-Item -Path $CONFIG_DIR -Recurse -Force
    Write-Host "✅ Deleted $CONFIG_DIR" -ForegroundColor Green
}

Write-Host "Deleting tool directory $TARGET_DIR ..."
if (Test-Path $TARGET_DIR) {
    # We might be running from this directory, so we should be careful.
    # But usually, it's fine as long as the files aren't locked.
    Remove-Item -Path $TARGET_DIR -Recurse -Force
    Write-Host "✅ Deleted $TARGET_DIR" -ForegroundColor Green
}

Write-Host "`n✅ Uninstallation complete!" -ForegroundColor Green
Write-Host "Please restart your terminal."
