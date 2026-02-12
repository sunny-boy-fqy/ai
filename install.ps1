# AI Tool Installation & Update Script for Windows
$CONFIG_DIR = "$HOME\.config\ai"
$USER_AI_DIR = "$HOME\.ai"
$MCP_SERVERS_DIR = "$USER_AI_DIR\mcp_servers"
$VENV_PATH = "$CONFIG_DIR\python_venv"

Write-Host "=== AI CLI Installation/Update (Windows) ===" -ForegroundColor Cyan

function Check-Command($cmd) {
    Get-Command $cmd -ErrorAction SilentlyContinue
}

# 1. Check Python
if (-not (Check-Command "python")) {
    Write-Host "Warning: Python not found." -ForegroundColor Yellow
    $useWinget = Read-Host "Try install Python 3 via winget? (y/n)"
    if ($useWinget -eq "y") {
        if (Check-Command "winget") {
            winget install Python.Python.3
            Write-Host "Python install command sent. Please restart script after installation."
            exit
        } else {
            Write-Host "Error: winget not found. Please install Python 3 manually from python.org." -ForegroundColor Red
            exit 1
        }
    } else { exit 1 }
}

# 2. Directory Setup
$DEFAULT_DIR = "$HOME\ai"
if (Test-Path "$CONFIG_DIR\base_path.config") {
    $DEFAULT_DIR = Get-Content "$CONFIG_DIR\base_path.config" | Select-Object -First 1
}
$TARGET_DIR = Read-Host "Input install path [Default: $DEFAULT_DIR]"
if ([string]::IsNullOrWhiteSpace($TARGET_DIR)) { $TARGET_DIR = $DEFAULT_DIR }
$TARGET_DIR = $TARGET_DIR.Trim().Trim('"')

if (-not (Test-Path $TARGET_DIR)) { mkdir $TARGET_DIR | Out-Null }

# 3. Node.js Local Setup
if (-not (Test-Path $CONFIG_DIR)) { mkdir $CONFIG_DIR | Out-Null }
$NODE_LOCAL_DIR = "$CONFIG_DIR\node"
if (-not (Test-Path "$NODE_LOCAL_DIR\node.exe")) {
    Write-Host "Installing private Node.js..." -ForegroundColor Cyan
    $NODE_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip"
    $TEMP_ZIP = "$env:TEMP\node.zip"
    Invoke-WebRequest -Uri $NODE_URL -OutFile $TEMP_ZIP
    Expand-Archive -Path $TEMP_ZIP -DestinationPath "$env:TEMP\node-temp" -Force
    if (-not (Test-Path $NODE_LOCAL_DIR)) { mkdir $NODE_LOCAL_DIR | Out-Null }
    $extracted = Get-ChildItem -Path "$env:TEMP\node-temp" -Directory | Select-Object -First 1
    Copy-Item -Path "$($extracted.FullName)\*" -Destination $NODE_LOCAL_DIR -Recurse -Force
    Remove-Item $TEMP_ZIP -Force
    Remove-Item "$env:TEMP\node-temp" -Recurse -Force
}
$LOCAL_NPX = "$NODE_LOCAL_DIR\npx.cmd"

# 4. Download Source
if (-not (Test-Path "$TARGET_DIR\.git")) {
    if (Check-Command "git") {
        git clone https://github.com/sunny-boy-fqy/ai.git "$TARGET_DIR"
    } else {
        $zipPath = "$env:TEMP\ai-main.zip"
        Invoke-WebRequest -Uri "https://github.com/sunny-boy-fqy/ai/archive/refs/heads/main.zip" -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\ai-temp" -Force
        $extractedDir = Get-ChildItem -Path "$env:TEMP\ai-temp" -Directory | Select-Object -First 1
        Copy-Item -Path "$($extractedDir.FullName)\*" -Destination "$TARGET_DIR" -Recurse -Force
        Remove-Item $zipPath -Force
        Remove-Item "$env:TEMP\ai-temp" -Recurse -Force
    }
} else {
    if (Check-Command "git") {
        Set-Location "$TARGET_DIR"
        git pull
    }
}

# 5. Save Config
if (-not (Test-Path $USER_AI_DIR)) { mkdir $USER_AI_DIR | Out-Null }
if (-not (Test-Path $MCP_SERVERS_DIR)) { mkdir $MCP_SERVERS_DIR | Out-Null }
$TARGET_DIR | Out-File -FilePath "$CONFIG_DIR\base_path.config" -Encoding UTF8 -NoNewline

# 6. Environment Setup
if (-not (Test-Path $VENV_PATH)) { python -m venv $VENV_PATH }
& "$VENV_PATH\Scripts\pip.exe" install --upgrade pip
& "$VENV_PATH\Scripts\pip.exe" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 7. MCP Config
$MCP_CONFIG_PATH = "$CONFIG_DIR\mcp_config.json"
if (-not (Test-Path $MCP_CONFIG_PATH)) {
    $mcp_content = @"
{
  "servers": {
    "filesystem": { "command": "$LOCAL_NPX", "args": ["-y", "@modelcontextprotocol/server-filesystem"], "type": "stdio" },
    "web-search": { "command": "$VENV_PATH\Scripts\python.exe", "args": ["$MCP_SERVERS_DIR\web_search_server.py"], "type": "stdio" }
  }
}
"@
    $mcp_content | Out-File -FilePath $MCP_CONFIG_PATH -Encoding utf8
}

# 8. PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$TARGET_DIR*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$TARGET_DIR", "User")
}

Write-Host "Success! Please restart terminal." -ForegroundColor Green
