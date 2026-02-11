@echo off
setlocal
chcp 65001 >nul
set CONFIG_DIR=%USERPROFILE%\.config\ai
if not exist "%CONFIG_DIR%\base_path.config" (
    echo [ERROR] AI CLI not initialized. Please run install.sh or install.ps1
    exit /b 1
)
set /p BASE_DIR=<"%CONFIG_DIR%\base_path.config"
"%CONFIG_DIR%\python_venv\Scripts\python.exe" "%BASE_DIR%\ai_caller.py" %*
endlocal
